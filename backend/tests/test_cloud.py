"""Exercise cloud routes without contacting a real user's storage or database."""
import contextlib
import http.client
import io
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from backend.server import App
from backend.cloud import CloudHandler, Database, Row

PNG=bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000b49444154789c636000020000050001a5f645400000000049454e44ae426082')
class Storage:
 def __init__(self):self.objects={};self.requests=[]
 def generate_presigned_url(self,operation,Params,ExpiresIn):
  self.requests.append((operation,Params,ExpiresIn));return 'https://storage.example/'+Params['Key']+'?signed=test'
 def head_object(self,Bucket,Key):return {'ContentLength':len(self.objects[Key])}
 def get_object(self,Bucket,Key,Range):return {'Body':io.BytesIO(self.objects[Key][:32])}
 def copy_object(self,Bucket,Key,CopySource):self.objects[Key]=self.objects[CopySource['Key']]
class Compat:
 def __init__(self,db):self.db=db
 def __getattr__(self,name):return getattr(self.db,name)
 def execute(self,sql,params=()):
  if 'pg_advisory_xact_lock' in sql:return self.db.execute('SELECT 1')
  return self.db.execute(sql.replace(' FOR UPDATE',''),params)
class TestApp(App):
 @contextlib.contextmanager
 def db(self):
  with super().db() as db:yield Compat(db)
 def signed_read(self,path):return self.storage.generate_presigned_url('get_object',{'Bucket':self.bucket,'Key':path},3600)

class CloudTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.app=TestApp(self.temp.name);self.app.storage=Storage();self.app.bucket='private-test'
  with self.app.db() as db:
   db.execute('CREATE TABLE login_attempts(key TEXT PRIMARY KEY,started REAL,attempts INTEGER)')
   db.execute('CREATE TABLE pending_uploads(id TEXT PRIMARY KEY,token TEXT,path TEXT,name TEXT,kind TEXT,collection TEXT,media_id TEXT,size INTEGER,expires REAL)')
  self.env=patch.dict(os.environ,{'PUBLIC_ORIGIN':'https://loveflix.example','VERCEL_URL':'preview.example'});self.env.start()
  self.app_patch=patch('backend.cloud.cloud_app',return_value=self.app);self.app_patch.start()
  self.server=ThreadingHTTPServer(('127.0.0.1',0),CloudHandler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.cookie=''
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join();self.app_patch.stop();self.env.stop();self.temp.cleanup()
 def request(self,path,data=None,method=None,auth=True,host='loveflix.example',origin=None):
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_port);headers={'Host':host,'Content-Type':'application/json','Origin':origin or 'https://'+host}
  if auth:headers['Cookie']=self.cookie
  c.request(method or ('POST' if data is not None else 'GET'),path,json.dumps(data) if data is not None else None,headers);r=c.getresponse();raw=r.read();result=(r.status,dict(r.getheaders()),json.loads(raw) if raw else None);c.close();return result
 def login(self):
  status,headers,_=self.request('/api/register',{'username':'cloud-user','password':'test-password-123'})
  self.assertEqual(status,200);self.assertIn('Secure',headers['Set-Cookie']);self.cookie=headers['Set-Cookie'].split(';')[0]
 def test_accounts_origin_and_state(self):
  self.login();self.assertEqual(self.request('/api/state')[2]['directUploads'],True)
  self.assertEqual(self.request('/api/state',auth=False)[0],401)
  self.assertEqual(self.request('/api/state',host='evil.example')[0],403)
  self.assertEqual(self.request('/api/logout',{},origin='https://evil.example')[0],403)
  self.assertEqual(self.request('/api/state',host='preview.example')[0],200)
  self.assertEqual(self.request('/api/register',{'username':'cloud-user','password':'test-password-123'})[0],409)
  self.assertEqual(self.request('/api/login',{'username':'cloud-user','password':'test-password-123'})[0],200)
  for _ in range(10):self.assertEqual(self.request('/api/login',{'username':'bad','password':'wrong'})[0],401)
  self.assertEqual(self.request('/api/login',{'username':'bad','password':'wrong'})[0],429)
 def test_direct_upload_validation_and_replacement(self):
  self.assertEqual(self.request('/api/uploads/prepare',{'name':'x.png'},auth=False)[0],401)
  self.login()
  self.assertEqual(self.request('/api/uploads/prepare',{'name':'x.png','size':300*1024**2,'collection':'gallery'})[0],400)
  _,_,upload=self.request('/api/uploads/prepare',{'name':'x.png','size':len(PNG),'collection':'gallery'})
  _,params,_=self.app.storage.requests[-1];self.assertEqual(params['ContentLength'],len(PNG));self.app.storage.objects[params['Key']]=PNG
  status,_,item=self.request('/api/uploads/complete',{'id':upload['id']});self.assertEqual(status,201)
  self.assertEqual(self.request('/api/uploads/complete',{'id':upload['id']})[0],409)
  status,headers,_=self.request(item['url']);self.assertEqual(status,307);self.assertIn('/uploads/',headers['Location'])
  self.app.storage.objects[params['Key']]=b'changed pending object'
  final_key='uploads/'+upload['id']+'.png';self.assertEqual(self.app.storage.objects[final_key],PNG)
  _,_,replacement=self.request('/api/uploads/prepare',{'name':'new.png','size':len(PNG),'collection':'gallery','id':item['id']})
  self.app.storage.objects[self.app.storage.requests[-1][1]['Key']]=PNG
  status,_,updated=self.request('/api/uploads/complete',{'id':replacement['id']});self.assertEqual(status,201);self.assertEqual(updated['id'],item['id']);self.assertEqual(updated['revision'],2)
  self.assertEqual(self.request('/api/media/'+item['id'],method='DELETE')[0],200)
  self.assertEqual(self.request(item['url'])[0],404)
 def test_private_files_and_invalid_upload(self):
  self.assertEqual(self.request('/images/us-1.jpeg',auth=False)[0],401)
  self.assertEqual(self.request('/backend/cloud.py')[0],404)
  self.assertEqual(self.request('/.env')[0],404)
  self.login();self.assertEqual(self.request('/images/us-1.jpeg')[0],307)
  _,_,upload=self.request('/api/uploads/prepare',{'name':'bad.png','size':5,'collection':'gallery'})
  self.app.storage.objects[self.app.storage.requests[-1][1]['Key']]=b'wrong'
  self.assertEqual(self.request('/api/uploads/complete',{'id':upload['id']})[0],400)
  with self.app.db() as db:self.assertIsNone(db.execute("SELECT 1 FROM media WHERE title='bad'").fetchone())
 def test_database_upsert_translation(self):
  class Connection:
   def execute(self,sql,params):self.sql=sql;self.params=params
  connection=Connection();db=Database(connection)
  db.execute('INSERT OR REPLACE INTO favorites VALUES(?,?,?)',('my','x','{}'))
  self.assertIn('ON CONFLICT(profile,id)',connection.sql);self.assertEqual(connection.params,('my','x','{}'))
  self.assertEqual(Row({'value':'x'})[0],'x')
