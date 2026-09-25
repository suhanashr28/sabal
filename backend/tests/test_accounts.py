import hashlib
import http.client
import json
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from backend.server import make_server

class AccountTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.server=make_server(0,self.tmp.name)
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
 def request(self,path,data=None,cookie=''):
  conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
  headers={'Host':f'localhost:{self.server.server_port}','Content-Type':'application/json'}
  if cookie:headers['Cookie']=cookie
  conn.request('POST' if data is not None else 'GET',path,json.dumps(data) if data is not None else None,headers)
  response=conn.getresponse();raw=response.read();result=(response.status,json.loads(raw) if raw else {},dict(response.getheaders()));conn.close();return result
 def register(self):
  return self.request('/api/accounts/register',{'name':'Test Person','email':'Person@Example.com','phone':'+977 9800000000','password':'first-password-123'})
 def test_registration_then_login_and_private_details(self):
  status,body,headers=self.register();self.assertEqual(status,200);self.assertNotIn('Set-Cookie',headers)
  self.assertEqual(self.register()[0],409)
  with self.server.app.db() as db:
   row=db.execute('SELECT * FROM account_details').fetchone();self.assertEqual(row['email'],'person@example.com');self.assertEqual(row['name'],'Test Person')
  result=self.request('/api/accounts/login',{'identity':'PERSON@example.com','password':'first-password-123'})
  self.assertEqual(result[0],200)
  state=self.request('/api/state',cookie=result[2]['Set-Cookie'].split(';')[0]);self.assertEqual(state[0],200);self.assertNotIn('person@example.com',json.dumps(state[1]))
  root=self.request('/');self.assertEqual(root[2]['Location'],'/login.html?mode=register')
 def test_recovery_is_single_use_and_revokes_sessions(self):
  self.register();login=self.request('/api/accounts/login',{'identity':'person@example.com','password':'first-password-123'});cookie=login[2]['Set-Cookie'].split(';')[0]
  with patch('backend.accounts.mail_configured',return_value=True),patch('backend.accounts.send_reset') as sender:
   known=self.request('/api/accounts/forgot',{'email':'person@example.com'})
   unknown=self.request('/api/accounts/forgot',{'email':'missing@example.com'})
   self.assertEqual(known[:2],unknown[:2]);self.assertEqual(sender.call_count,1);token=sender.call_args.args[1]
  with self.server.app.db() as db:
   row=db.execute('SELECT token FROM password_resets').fetchone();self.assertEqual(row['token'],hashlib.sha256(token.encode()).hexdigest())
  payload={'token':token,'password':'second-password-456'}
  self.assertEqual(self.request('/api/accounts/reset',payload)[0],200)
  self.assertEqual(self.request('/api/accounts/reset',payload)[0],400)
  self.assertEqual(self.request('/api/state',cookie=cookie)[0],401)
  self.assertEqual(self.request('/api/accounts/login',{'identity':'person@example.com','password':'first-password-123'})[0],401)
  self.assertEqual(self.request('/api/accounts/login',{'identity':'person@example.com','password':'second-password-456'})[0],200)
 def test_invalid_expired_and_unconfigured_recovery(self):
  self.assertEqual(self.request('/api/accounts/register',{'name':'Test','email':'bad','phone':'123','password':'short'})[0],400)
  self.register()
  with patch('backend.accounts.mail_configured',return_value=False):self.assertEqual(self.request('/api/accounts/forgot',{'email':'person@example.com'})[0],503)
  with self.server.app.db() as db:
   uid=db.execute('SELECT id FROM users').fetchone()['id'];db.execute('INSERT INTO password_resets VALUES(?,?,?)',(hashlib.sha256(b'expired').hexdigest(),uid,time.time()-1))
  self.assertEqual(self.request('/api/accounts/reset',{'token':'expired','password':'long-password-123'})[0],400)
 def test_recovery_rate_limit(self):
  with patch('backend.accounts.mail_configured',return_value=True):
   for _ in range(3):self.assertEqual(self.request('/api/accounts/forgot',{'email':'unknown@example.com'})[0],200)
   self.assertEqual(self.request('/api/accounts/forgot',{'email':'unknown@example.com'})[0],429)

 def test_change_password_requires_current_password_and_revokes_sessions(self):
  self.register()
  login=self.request('/api/accounts/login',{'identity':'person@example.com','password':'first-password-123'})
  cookie=login[2]['Set-Cookie'].split(';')[0]
  payload={'current_password':'first-password-123','password':'replacement-password'}
  self.assertEqual(self.request('/api/accounts/change-password',payload)[0],401)
  self.assertEqual(self.request('/api/accounts/change-password',dict(payload,current_password='incorrect'),cookie)[0],403)
  self.assertEqual(self.request('/api/accounts/change-password',payload,cookie)[0],200)
  self.assertEqual(self.request('/api/state',cookie=cookie)[0],401)
  self.assertEqual(self.request('/api/accounts/login',{'identity':'person@example.com','password':'first-password-123'})[0],401)
  self.assertEqual(self.request('/api/accounts/login',{'identity':'person@example.com','password':'replacement-password'})[0],200)

 def test_favorites_and_profile_survive_logout_and_new_login(self):
  self.register()
  login=lambda:self.request('/api/accounts/login',{'identity':'person@example.com','password':'first-password-123'})[2]['Set-Cookie'].split(';')[0]
  cookie=login()
  self.assertEqual(self.request('/api/accounts/profile',{'profile':'my'},cookie)[0],200)
  conn=http.client.HTTPConnection('localhost',self.server.server_port)
  item={'id':'page:love-story.html','title':'Our story','href':'love-story.html','image':''}
  conn.request('PUT','/api/favorites/my',json.dumps(item),{'Content-Type':'application/json','Cookie':cookie})
  response=conn.getresponse();self.assertEqual(response.status,200);response.read();conn.close()
  self.assertEqual(self.request('/api/logout',{},cookie)[0],200)
  self.assertEqual(self.request('/api/state',cookie=cookie)[0],401)
  state=self.request('/api/state',cookie=login())[1]
  self.assertEqual(state['activeProfile'],'my')
  self.assertEqual(state['favorites']['my'],[item])
  self.assertEqual(state['favorites']['sabal'],[])
