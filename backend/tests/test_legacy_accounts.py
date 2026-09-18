import http.client
import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('account_server',Path(__file__).resolve().parents[1]/'server.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class AccountTests(unittest.TestCase):
 def test_existing_owner_and_new_accounts(self):
  with tempfile.TemporaryDirectory() as directory:
   app=m.App(directory)
   salt='ab'*16
   password='original-password'
   digest=m.hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
   with app.db() as db:
    # Recreate the pre-account-details schema used by the original app.
    for table in ['account_details','account_sessions','password_resets']:
     db.execute(f'DROP TABLE {table}')
    db.execute('DROP TABLE users')
    db.execute('CREATE TABLE users(id INTEGER PRIMARY KEY CHECK(id=1),username TEXT NOT NULL,salt TEXT NOT NULL,password TEXT NOT NULL)')
    db.execute('INSERT INTO users VALUES(1,?,?,?)',('owner',salt,digest))
   server=m.make_server(0,directory)
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   def request(path,data=None,cookie=None):
    c=http.client.HTTPConnection('127.0.0.1',server.server_port)
    headers={'Content-Type':'application/json'}
    if cookie: headers['Cookie']=cookie
    c.request('POST' if data is not None else 'GET',path,json.dumps(data) if data is not None else None,headers)
    r=c.getresponse();result=(r.status,r.getheader('Set-Cookie'),r.read());c.close();return result
   try:
    self.assertEqual(request('/api/login',{'username':'owner','password':password})[0],200)
    self.assertEqual(request('/api/register',{'username':'friend','password':'short'})[0],400)
    credentials={'username':'friend','password':'friend-password'}
    status,cookie,_=request('/api/register',credentials);self.assertEqual(status,200)
    self.assertEqual(request('/api/state',cookie=cookie.split(';')[0])[0],200)
    self.assertEqual(request('/api/register',credentials)[0],409)
    self.assertEqual(request('/api/login',credentials)[0],200)
    self.assertEqual(request('/api/login',{'username':'friend','password':password})[0],401)
    self.assertEqual(request('/api/login',{'username':'missing','password':password})[0],401)
    self.assertEqual(request('/api/state')[0],401)
    m.App(directory)
    with app.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],2)
   finally:server.shutdown();server.server_close();thread.join()
