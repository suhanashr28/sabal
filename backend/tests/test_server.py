import datetime as dt
import http.client
import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('loveflix_server',Path(__file__).resolve().parents[1]/'server.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
PNG=bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000b49444154789c636000020000050001a5f645400000000049454e44ae426082')
class BackendTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.server=m.make_server(0,cls.temp.name);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.port=cls.server.server_port;cls.cookie=''
 @classmethod
 def tearDownClass(cls):
  cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.temp.cleanup()
 def request(self,method,path,data=None,auth=True,headers=None):
  h={'Host':f'localhost:{self.port}'}
  if auth and self.cookie:h['Cookie']=self.cookie
  if isinstance(data,dict):data=json.dumps(data).encode();h['Content-Type']='application/json'
  h.update(headers or {})
  c=http.client.HTTPConnection('127.0.0.1',self.port);c.request(method,path,data,h);r=c.getresponse();body=r.read();status=r.status;rh=dict(r.getheaders());c.close()
  try:body=json.loads(body)
  except (ValueError,UnicodeDecodeError):pass
  return status,body,rh
 def test_01_setup_and_auth(self):
  self.assertTrue(self.request('GET','/api/setup-state')[1]['needsSetup'])
  self.assertEqual(self.request('GET','/api/state',auth=False)[0],401)
  self.assertEqual(self.request('GET','/images/us-1.jpeg',auth=False)[0],302)
  self.assertEqual(self.request('POST','/api/setup',{'username':'test-owner','password':'short'})[0],400)
  status,body,headers=self.request('POST','/api/setup',{'username':'test-owner','password':'test-password-12345'})
  self.assertEqual(status,200);type(self).cookie=headers['Set-Cookie'].split(';')[0];self.assertIn('HttpOnly',headers['Set-Cookie'])
  self.assertEqual(self.request('POST','/api/setup',{'username':'test-owner','password':'test-password-12345'})[0],409)
  self.assertEqual(self.request('POST','/api/login',{'username':'test-owner','password':'wrong'})[0],401)
  self.assertEqual(self.request('GET','/api/state')[0],200)
 def test_02_media_crud_and_range(self):
  status,item,_=self.request('POST','/api/media',PNG,headers={'X-File-Name':'test.png','X-Collection':'gallery','Content-Type':'image/png'})
  self.assertEqual(status,201);mid=item['id'];url=item['url'];self.assertEqual(item['collections'],['gallery'])
  self.assertEqual(self.request('GET',url)[1],PNG)
  status,body,headers=self.request('GET',url,headers={'Range':'bytes=0-7'});self.assertEqual(status,206);self.assertEqual(body,PNG[:8]);self.assertIn('Content-Range',headers)
  self.assertEqual(self.request('GET',url,headers={'Range':'bytes=9999-'})[0],416)
  self.assertEqual(self.request('PATCH',f'/api/media/{mid}',{'title':'Edited title','caption':'Saved caption','collections':['family']})[0],200)
  item=next(x for x in self.request('GET','/api/state')[1]['media'] if x['id']==mid);self.assertEqual(item['title'],'Edited title');self.assertEqual(item['collections'],['family'])
  self.assertEqual(self.request('POST',f'/api/media/{mid}/file',PNG,headers={'X-File-Name':'new.png'})[0],201)
  self.assertEqual(self.request('DELETE',f'/api/media/{mid}')[0],200);self.assertEqual(self.request('GET',url)[0],404)
  self.assertEqual(self.request('PATCH',f'/api/media/{mid}',{'title':'Restored','caption':'Saved','collections':['gallery'],'restore':True})[0],200)
  self.assertEqual(self.request('GET',url)[0],200)
 def test_03_settings_profiles_favorites_and_content(self):
  settings={'start_date':'2020-02-29','timezone':'Asia/Kathmandu'}
  self.assertEqual(self.request('PATCH','/api/settings',settings)[0],200)
  self.assertEqual(self.request('PATCH','/api/settings',{'start_date':'2099-01-01','timezone':'Asia/Kathmandu'})[0],400)
  self.assertEqual(self.request('PATCH','/api/settings',{'start_date':'2020-01-01','timezone':'Bad/Zone'})[0],400)
  self.assertEqual(self.request('PATCH','/api/profiles/my',{'name':'Test Name','picture':''})[0],200)
  favorite={'id':'test-favorite','title':'A saved memory','href':'home.html','image':''}
  self.assertEqual(self.request('PUT','/api/favorites/my',favorite)[0],200)
  self.assertEqual(self.request('PUT','/api/favorites/my',favorite)[0],200)
  state=self.request('GET','/api/state')[1];self.assertEqual(len(state['favorites']['my']),1);self.assertEqual(len(state['favorites']['sabal']),0)
  content={'page':'home.html','selector':'[data-edit-id="text-1"]','text':'A new title'}
  self.assertEqual(self.request('PUT','/api/content',content)[0],200)
  reopened=m.App(self.temp.name).state();self.assertEqual(reopened['settings'],settings);self.assertEqual(reopened['profiles'][0]['name'],'Test Name');self.assertEqual(reopened['content'][0]['text'],'A new title');self.assertEqual(len(reopened['favorites']['my']),1)
  self.assertEqual(self.request('DELETE','/api/favorites/my',favorite)[0],200)
  self.assertEqual(self.request('DELETE','/api/content',content)[0],200)
 def test_04_boundaries(self):
  self.assertEqual(self.request('GET','/backend/data/loveflix.sqlite3')[0],404)
  self.assertEqual(self.request('GET','/.git/config')[0],404)
  self.assertEqual(self.request('GET','/%2e%2e/backend/server.py')[0],404)
  self.assertEqual(self.request('GET','/api/state',headers={'Host':'evil.example'})[0],403)
  self.assertEqual(self.request('POST','/api/logout',headers={'Origin':'https://evil.example'})[0],403)
  self.assertEqual(self.request('POST','/api/media',b'<script>alert(1)</script>',headers={'X-File-Name':'fake.png'})[0],400)
  self.assertEqual(self.request('POST','/api/media',PNG,headers={'X-File-Name':'test.svg'})[0],400)
  self.assertEqual(self.request('PUT','/api/favorites/my',{'id':'evil','title':'evil','href':'javascript:alert(1)'})[0],400)
  self.assertEqual(self.request('PATCH','/api/profiles/my',{'name':'X','picture':'https://evil.example/a.png'})[0],400)
 def test_05_logout(self):
  self.assertEqual(self.request('POST','/api/logout')[0],200);self.assertEqual(self.request('GET','/api/state')[0],401)
 def test_06_counter(self):
  settings={'start_date':'2023-04-27','timezone':'Asia/Kathmandu'}
  before=m.counter(settings,dt.datetime(2026,4,26,18,14,tzinfo=dt.timezone.utc));after=m.counter(settings,dt.datetime(2026,4,26,18,15,tzinfo=dt.timezone.utc))
  self.assertEqual(before['years'],2);self.assertEqual(after['years'],3);self.assertTrue(after['anniversary']);self.assertEqual(after['days'],before['days']+1)
  leap=m.counter({'start_date':'2020-02-29','timezone':'UTC'},dt.datetime(2023,2,28,tzinfo=dt.timezone.utc));self.assertEqual(leap['years'],3);self.assertTrue(leap['anniversary'])
if __name__=='__main__':unittest.main()
