#!/usr/bin/env python3
"""LoveFlix local server. Python 3.11+, no third-party dependencies."""
from contextlib import contextmanager
import argparse, datetime as dt, hashlib, hmac, json, mimetypes, os, re, secrets, sqlite3, threading, time
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parent.parent
COLLECTIONS = ['gallery','first-date','story-begins','best-part','favorite','birthday','family','airport','nagarkot','videos','play']
MAX_UPLOAD = 250 * 1024 * 1024
class APIError(Exception):
 def __init__(self, message, status=400): self.message, self.status = message, status

def counter(settings, now=None):
 zone = ZoneInfo(settings['timezone'])
 now = now or dt.datetime.now(zone)
 today = now.astimezone(zone).date()
 start = dt.date.fromisoformat(settings['start_date'])
 def anniversary(year):
  try: return start.replace(year=year)
  except ValueError: return dt.date(year, 2, 28)
 years = max(0, today.year-start.year-(today < anniversary(today.year)))
 next_year = max(start.year+1, today.year if today < anniversary(today.year) else today.year+1)
 return dict(days=max(0,(today-start).days), years=years, next_date=anniversary(next_year).isoformat(), next_years=next_year-start.year, remaining=(anniversary(next_year)-today).days, today=today.isoformat(), anniversary=today == anniversary(today.year) and years>0)

class App:
 def __init__(self, data):
  self.data = Path(data); self.data.mkdir(parents=True,exist_ok=True)
  self.uploads = self.data/'uploads'; self.uploads.mkdir(exist_ok=True)
  self.dbpath = self.data/'loveflix.sqlite3'; self.lock=threading.Lock(); self.attempts={}
  with self.db() as db:
   db.executescript('''
   CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY CHECK(id=1),username TEXT NOT NULL,salt TEXT NOT NULL,password TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,expires REAL NOT NULL);
   CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1),value TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY,name TEXT NOT NULL,picture TEXT NOT NULL DEFAULT '');
   CREATE TABLE IF NOT EXISTS media(id TEXT PRIMARY KEY,original TEXT NOT NULL,path TEXT NOT NULL,kind TEXT NOT NULL,title TEXT NOT NULL,caption TEXT NOT NULL DEFAULT '',collections TEXT NOT NULL,deleted INTEGER NOT NULL DEFAULT 0,revision INTEGER NOT NULL DEFAULT 1,created REAL NOT NULL);
   CREATE TABLE IF NOT EXISTS favorites(profile TEXT NOT NULL,id TEXT NOT NULL,value TEXT NOT NULL,PRIMARY KEY(profile,id));
   CREATE TABLE IF NOT EXISTS content(page TEXT NOT NULL,selector TEXT NOT NULL,text TEXT NOT NULL,PRIMARY KEY(page,selector));
   ''')
   schema=db.execute("SELECT sql FROM sqlite_master WHERE name='users'").fetchone()[0]
   if 'CHECK' in schema.upper():
    db.execute('ALTER TABLE users RENAME TO legacy_users')
    db.execute('CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT NOT NULL UNIQUE,salt TEXT NOT NULL,password TEXT NOT NULL)')
    db.execute('INSERT INTO users SELECT * FROM legacy_users')
    db.execute('DROP TABLE legacy_users')
   db.execute('INSERT OR IGNORE INTO settings VALUES(1,?)',(json.dumps(dict(start_date='2023-04-27',timezone='Asia/Kathmandu')),))
   db.executemany('INSERT OR IGNORE INTO profiles(id,name) VALUES(?,?)',[('my','My Profile'),('sabal','Sabal')])
   seeded = db.execute('SELECT count(*) FROM media').fetchone()[0]
   if not seeded:
    paths=sorted([*ROOT.glob('images/*'),*ROOT.glob('videos/*.mp4'),ROOT/'birthday.mp4',ROOT/'play/birthday-film.mp4'])
    for p in paths:
     if not p.is_file() or p.suffix.lower() not in ['.jpeg','.jpg','.png','.webp','.gif','.mp4','.webm','.mov']: continue
     rel=p.relative_to(ROOT).as_posix(); kind='video' if p.suffix.lower() in ['.mp4','.webm','.mov'] else 'photo'
     prefix=p.stem.split('-')[0]; collection={'us':'gallery','favorite':'favorite','best':'best-part','story':'story-begins','first':'first-date'}.get(prefix,prefix)
     groups=[collection] if collection in COLLECTIONS else ['gallery']
     mid=hashlib.sha256(rel.encode()).hexdigest()[:20]
     if rel=='birthday.mp4': groups=['videos','birthday']
     if rel=='play/birthday-film.mp4': groups=['play']; mid='play-movie'
     title=p.stem.replace('-',' ').title(); caption=''
     if re.fullmatch(r'us-\d+',p.stem):
      stories=json.loads((ROOT/'backend/gallery-stories.json').read_text())
      index=int(p.stem.split('-')[1])-1
      if index<len(stories): title,caption=stories[index]
     db.execute('INSERT INTO media(id,original,path,kind,title,caption,collections,created) VALUES(?,?,?,?,?,?,?,?)',(mid,rel,rel,kind,title,caption,json.dumps(groups),p.stat().st_mtime))
   # Give the story cover its own editable media record on existing installations.
   cover=ROOT/'images/our-story-cover.jpeg'
   if cover.is_file():
    db.execute('INSERT OR IGNORE INTO media(id,original,path,kind,title,caption,collections,created) VALUES(?,?,?,?,?,?,?,?)',(hashlib.sha256(b'images/our-story-cover.jpeg').hexdigest()[:20],'images/our-story-cover.jpeg','images/our-story-cover.jpeg','photo','Our Story Cover','','[]',cover.stat().st_mtime))
 @contextmanager
 def db(self):
  db=sqlite3.connect(self.dbpath,timeout=15); db.row_factory=sqlite3.Row; db.execute('PRAGMA foreign_keys=ON')
  try:
   with db: yield db
  finally: db.close()
 def setup(self):
  with self.db() as db: return db.execute('SELECT 1 FROM users').fetchone() is None
 def media(self,row):
  out=dict(row); out['collections']=json.loads(out['collections']); out['url']=f"/media/{out['id']}?v={out['revision']}"; del out['path']; return out
 def state(self):
  with self.db() as db:
   settings=json.loads(db.execute('SELECT value FROM settings WHERE id=1').fetchone()[0])
   return dict(settings=settings,counter=counter(settings),profiles=[dict(r) for r in db.execute('SELECT * FROM profiles')],media=[self.media(r) for r in sorted(db.execute('SELECT * FROM media'),key=lambda r:(not bool(r['original']),re.sub(r'\d+',lambda m:m.group().zfill(6),r['original']) if r['original'] else str(r['created'])))], favorites={p:[json.loads(r[0]) for r in db.execute('SELECT value FROM favorites WHERE profile=?',(p,))] for p in ['my','sabal']},collections=COLLECTIONS,content=[dict(r) for r in db.execute('SELECT * FROM content')])

class Handler(BaseHTTPRequestHandler):
 server_version='LoveFlix'
 @property
 def app(self): return self.server.app
 def headers_common(self):
  self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','same-origin'); self.send_header('X-Frame-Options','SAMEORIGIN'); self.send_header('Cache-Control','no-store')
 def reply(self,obj,status=200,cookie=None):
  body=json.dumps(obj).encode(); self.send_response(status); self.headers_common(); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body)))
  if cookie: self.send_header('Set-Cookie',cookie)
  self.end_headers(); self.wfile.write(body)
 def token(self):
  c=cookies.SimpleCookie()
  try: c.load(self.headers.get('Cookie','')); value=c.get('lf_session'); return hashlib.sha256(value.value.encode()).hexdigest() if value else ''
  except cookies.CookieError: return ''
 def authorized(self):
  with self.app.db() as db: return db.execute('SELECT 1 FROM sessions WHERE token=? AND expires>?',(self.token(),time.time())).fetchone() is not None
 def session(self,remember=False):
  raw=secrets.token_urlsafe(32); duration=30*86400 if remember else 12*3600
  with self.app.db() as db:
   db.execute('DELETE FROM sessions WHERE expires<?',(time.time(),)); db.execute('INSERT INTO sessions VALUES(?,?)',(hashlib.sha256(raw.encode()).hexdigest(),time.time()+duration))
  return f'lf_session={raw}; HttpOnly; SameSite=Strict; Path=/; Max-Age={duration}'
 def body(self,limit=1000000):
  try: size=int(self.headers.get('Content-Length','0'))
  except ValueError: raise APIError('Invalid upload size.')
  if size<=0 or size>limit: raise APIError(f'File is too large. Maximum {limit//1024//1024} MB.' if size>limit else 'No data received.',413 if size>limit else 400)
  body=self.rfile.read(size)
  if len(body)!=size: raise APIError('Upload was interrupted.')
  return body
 def json_body(self):
  if self.headers.get('Content-Type','').split(';')[0]!='application/json': raise APIError('Expected JSON.',415)
  try: data=json.loads(self.body())
  except (ValueError,UnicodeDecodeError): raise APIError('Invalid JSON.')
  if not isinstance(data,dict): raise APIError('Expected an object.')
  return data
 def text(self,data,key,limit=200,required=False):
  value=data.get(key,'')
  if not isinstance(value,str) or len(value)>limit or (required and not value.strip()): raise APIError(f'Please enter a valid {key.replace("_"," ")}.')
  return value.strip()
 def protect(self,mutation=False):
  host=self.headers.get('Host','')
  if host not in [f'localhost:{self.server.server_port}',f'127.0.0.1:{self.server.server_port}', '127.0.0.1:5500', 'localhost:5500']: raise APIError('Invalid host.',403)
  if mutation:
   origin=self.headers.get('Origin')
   if origin and origin!=f'http://{host}': raise APIError('Cross-site requests are not allowed.',403)
   if self.headers.get('Sec-Fetch-Site')=='cross-site': raise APIError('Cross-site requests are not allowed.',403)
 def do_GET(self): self.dispatch('GET')
 def do_POST(self): self.dispatch('POST')
 def do_PATCH(self): self.dispatch('PATCH')
 def do_PUT(self): self.dispatch('PUT')
 def do_DELETE(self): self.dispatch('DELETE')
 def do_HEAD(self): self.dispatch('HEAD')
 def dispatch(self,method):
  try:
   self.protect(method not in ['GET','HEAD']); self.route(method)
  except APIError as e: self.reply({'error':e.message},e.status)
  except (BrokenPipeError,ConnectionResetError): pass
  except Exception:
   import traceback; traceback.print_exc(); self.reply({'error':'Could not save this change. Please try again.'},500)
 def route(self,method):
  path=unquote(urlsplit(self.path).path)
  if path=='/api/setup-state' and method=='GET': return self.reply(dict(needsSetup=self.app.setup(),authenticated=self.authorized()))
  if path in ['/api/setup','/api/register','/api/login'] and method=='POST':
   data=self.json_body(); username=self.text(data,'username',80,True); password=self.text(data,'password',200,True)
   if path in ['/api/setup','/api/register']:
    if len(password)<10: raise APIError('Use a password with at least 10 characters.')
    with self.app.lock:
     if path=='/api/setup' and not self.app.setup(): raise APIError('Your account already exists. Please sign in.',409)
     salt=secrets.token_hex(16); digest=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
     with self.app.db() as db:
      if db.execute('SELECT 1 FROM users WHERE username=?',(username,)).fetchone(): raise APIError('This username is taken. Choose another one.',409)
      db.execute('INSERT INTO users(username,salt,password) VALUES(?,?,?)',(username,salt,digest))
   else:
    ip=self.client_address[0]
    with self.app.lock:
     attempts=[t for t in self.app.attempts.get(ip,[]) if t>time.time()-300]
     if len(attempts)>=10: raise APIError('Too many attempts. Try again in five minutes.',429)
     attempts.append(time.time()); self.app.attempts[ip]=attempts
    with self.app.db() as db: user=db.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
    if not user: raise APIError('Username or password is incorrect.',401)
    digest=hashlib.scrypt(password.encode(),salt=bytes.fromhex(user['salt']),n=16384,r=8,p=1).hex()
    if not hmac.compare_digest(digest,user['password']) or not hmac.compare_digest(username.encode(),user['username'].encode()): raise APIError('Username or password is incorrect.',401)
    with self.app.lock: self.app.attempts.pop(ip,None)
   return self.reply({'ok':True},cookie=self.session(bool(data.get('remember'))))
  if path.startswith('/api/') or path.startswith('/media/'):
   if not self.authorized(): raise APIError('Please sign in.',401)
  if path=='/api/logout' and method=='POST':
   with self.app.db() as db: db.execute('DELETE FROM sessions WHERE token=?',(self.token(),))
   return self.reply({'ok':True},cookie='lf_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
  if path=='/api/state' and method=='GET': return self.reply(self.app.state())
  if path=='/api/counter' and method=='GET':
   with self.app.db() as db: settings=json.loads(db.execute('SELECT value FROM settings WHERE id=1').fetchone()[0])
   return self.reply(dict(settings=settings,counter=counter(settings)))
  if path=='/api/settings' and method=='PATCH':
   data=self.json_body(); date=self.text(data,'start_date',10,True); zone=self.text(data,'timezone',80,True)
   try:
    start=dt.date.fromisoformat(date); tz=ZoneInfo(zone)
    if start>dt.datetime.now(tz).date(): raise ValueError()
   except (ValueError,ZoneInfoNotFoundError): raise APIError('Choose a valid past or present date and time zone.')
   with self.app.db() as db: db.execute('UPDATE settings SET value=? WHERE id=1',(json.dumps(dict(start_date=date,timezone=zone)),))
   return self.reply({'ok':True})
  if path.startswith('/api/profiles/') and method=='PATCH':
   pid=path.rsplit('/',1)[-1]
   if pid not in ['my','sabal']: raise APIError('Profile not found.',404)
   data=self.json_body(); name=self.text(data,'name',60,True); picture=self.text(data,'picture',100)
   if picture and not re.fullmatch(r'/media/[a-zA-Z0-9-]+(?:\?v=\d+)?',picture): raise APIError('Choose an uploaded profile picture.')
   if picture:
    with self.app.db() as db: row=db.execute('SELECT 1 FROM media WHERE id=? AND kind="photo" AND deleted=0',(picture.split('/')[-1].split('?')[0],)).fetchone()
    if not row: raise APIError('Picture not found.')
   with self.app.db() as db: db.execute('UPDATE profiles SET name=?,picture=? WHERE id=?',(name,picture,pid))
   return self.reply({'ok':True})
  if path.startswith('/api/favorites/') and method in ['PUT','DELETE']:
   pid=path.rsplit('/',1)[-1]
   if pid not in ['my','sabal']: raise APIError('Profile not found.',404)
   data=self.json_body(); fid=self.text(data,'id',250,True)
   with self.app.db() as db:
    if method=='DELETE': db.execute('DELETE FROM favorites WHERE profile=? AND id=?',(pid,fid))
    else:
     item={k:self.text(data,k,500,k in ['title','href']) for k in ['title','href','image']}; item['id']=fid
     for key in ['href','image']:
      val=item[key]
      if val and (val.startswith('//') or '\\' in val or ':' in val or '..' in val.split('/')): raise APIError('Only site links can be saved.')
     db.execute('INSERT OR REPLACE INTO favorites VALUES(?,?,?)',(pid,fid,json.dumps(item)))
   return self.reply({'ok':True})
  if path=='/api/content' and method in ['PUT','DELETE']:
   data=self.json_body(); page=self.text(data,'page',120,True); selector=self.text(data,'selector',150,True); text=self.text(data,'text',20000)
   if not re.fullmatch(r'[a-z-]+\.html(?:\?memory=[a-z-]+)?',page) or not re.fullmatch(r'\[data-edit-id="[a-z0-9-]+"\]',selector): raise APIError('Invalid page or text field.')
   with self.app.db() as db:
    if method=='DELETE': db.execute('DELETE FROM content WHERE page=? AND selector=?',(page,selector))
    else: db.execute('INSERT OR REPLACE INTO content VALUES(?,?,?)',(page,selector,text))
   return self.reply({'ok':True})
  if path=='/api/media' and method=='POST': return self.upload()
  if path.startswith('/api/media/'):
   mid=path.split('/')[3]
   with self.app.db() as db: row=db.execute('SELECT * FROM media WHERE id=?',(mid,)).fetchone()
   if not row: raise APIError('Media not found.',404)
   if path.endswith('/file') and method=='POST': return self.upload(mid)
   if method=='DELETE':
    with self.app.db() as db:
     db.execute('UPDATE media SET deleted=1,revision=revision+1 WHERE id=?',(mid,)); db.execute('DELETE FROM favorites WHERE id=?',(f'media:{mid}',))
    return self.reply({'ok':True})
   if method=='PATCH':
    data=self.json_body(); title=self.text(data,'title',200,True); caption=self.text(data,'caption',5000); groups=data.get('collections',json.loads(row['collections']))
    if not isinstance(groups,list) or not groups or any(g not in COLLECTIONS for g in groups): raise APIError('Choose a valid album.')
    if 'play' in groups and mid!='play-movie': raise APIError('Replace the existing Play movie to change the home movie.')
    if mid=='play-movie' and groups!=['play']: raise APIError('The home movie stays in Play.')
    with self.app.db() as db: db.execute('UPDATE media SET title=?,caption=?,collections=?,deleted=?,revision=revision+1 WHERE id=?',(title,caption,json.dumps(groups),0 if data.get('restore') else row['deleted'],mid))
    return self.reply({'ok':True})
  if path.startswith('/media/') and method in ['GET','HEAD']:
   with self.app.db() as db: row=db.execute('SELECT path FROM media WHERE id=? AND deleted=0',(path.split('/')[-1],)).fetchone()
   if not row: raise APIError('Media not found.',404)
   p=(self.app.data/row['path']) if row['path'].startswith('uploads/') else ROOT/row['path']
   return self.send_file(p,method)
  if path.startswith('/api/'): raise APIError('Endpoint not found.',404)
  if method not in ['GET','HEAD']: raise APIError('Method not allowed.',405)
  if path=='/': path='/index.html'
  if path.endswith('/'): path+='index.html'
  rel=path.lstrip('/'); p=(ROOT/rel).resolve()
  if not p.is_relative_to(ROOT) or any(x.startswith('.') for x in Path(rel).parts): raise APIError('Not found.',404)
  allowed=(len(Path(rel).parts)==1 and p.suffix in ['.html','.css','.js']) or (Path(rel).parts[0] in ['images','videos','play'] and p.suffix in ['.html','.css','.js','.mp4','.jpeg','.jpg','.png','.svg','.webp','.gif'])
  if not allowed: raise APIError('Not found.',404)
  public=rel=='login.html' or (len(Path(rel).parts)==1 and p.suffix in ['.css','.js'])
  if not public and not self.authorized():
   self.send_response(302); self.send_header('Location','/login.html'); self.send_header('Content-Length','0'); self.end_headers(); return
  return self.send_file(p,method)
 def upload(self,mid=None):
  name=unquote(self.headers.get('X-File-Name','upload')); ext=Path(name).suffix.lower(); group=self.headers.get('X-Collection','gallery')
  if group not in COLLECTIONS+['profile']: raise APIError('Invalid album.')
  if group=='play' and not mid: raise APIError('Use Replace file on the Play movie.')
  if ext not in ['.jpg','.jpeg','.png','.webp','.gif','.mp4','.webm','.mov']: raise APIError('Choose JPG, PNG, WebP, GIF, MP4, WebM, or MOV.')
  data=self.body(MAX_UPLOAD); head=data[:32]; kind='video' if ext in ['.mp4','.webm','.mov'] else 'photo'
  valid=(ext in ['.jpg','.jpeg'] and head.startswith(b'\xff\xd8\xff')) or (ext=='.png' and head.startswith(b'\x89PNG\r\n\x1a\n')) or (ext=='.gif' and head[:6] in [b'GIF87a',b'GIF89a']) or (ext=='.webp' and head[:4]==b'RIFF' and head[8:12]==b'WEBP') or (ext in ['.mp4','.mov'] and b'ftyp' in head) or (ext=='.webm' and head.startswith(b'\x1aE\xdf\xa3'))
  if not valid: raise APIError('This file does not match its media type.')
  if group=='videos' and kind!='video': raise APIError('Choose a video for the Video Library.')
  if group=='profile' and kind!='photo': raise APIError('Choose a photo for your profile.')
  if mid:
   with self.app.db() as db: row=db.execute('SELECT * FROM media WHERE id=?',(mid,)).fetchone()
   if row['kind']!=kind: raise APIError(f'Replace this item with another {row["kind"]}.')
  filename=secrets.token_hex(20)+ext; path=self.app.uploads/filename; path.write_bytes(data)
  try:
   with self.app.db() as db:
    if mid: db.execute('UPDATE media SET path=?,revision=revision+1 WHERE id=?',(f'uploads/{filename}',mid))
    else:
     mid=secrets.token_hex(12); db.execute('INSERT INTO media(id,original,path,kind,title,collections,created) VALUES(?,?,?,?,?,?,?)',(mid,'',f'uploads/{filename}',kind,Path(name).stem[:200],json.dumps([] if group=='profile' else [group]),time.time()))
    row=db.execute('SELECT * FROM media WHERE id=?',(mid,)).fetchone()
  except Exception:
   path.unlink(missing_ok=True); raise
  return self.reply(self.app.media(row),201)
 def send_file(self,path,method):
  if not path.is_file(): raise APIError('File not found.',404)
  size=path.stat().st_size; start=0; end=size-1; status=200; range_header=self.headers.get('Range')
  if range_header:
   match=re.fullmatch(r'bytes=(\d*)-(\d*)',range_header)
   if not match or not any(match.groups()): raise APIError('Invalid byte range.',416)
   a,b=match.groups()
   if not a: start=max(0,size-int(b))
   else: start=int(a); end=min(int(b),end) if b else end
   if start>=size or start>end:
    self.send_response(416); self.send_header('Content-Range',f'bytes */{size}'); self.send_header('Content-Length','0'); self.end_headers(); return
   status=206
  self.send_response(status); self.headers_common(); self.send_header('Content-Type',mimetypes.guess_type(path.name)[0] or 'application/octet-stream'); self.send_header('Accept-Ranges','bytes'); self.send_header('Content-Length',str(end-start+1))
  if status==206: self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
  self.end_headers()
  if method=='HEAD': return
  with path.open('rb') as stream:
   stream.seek(start); remaining=end-start+1
   while remaining>0:
    chunk=stream.read(min(65536,remaining))
    if not chunk: break
    self.wfile.write(chunk); remaining-=len(chunk)

def make_server(port=8787,data=None):
 server=ThreadingHTTPServer(('127.0.0.1',port),Handler); server.app=App(data or ROOT/'backend/data'); return server
if __name__=='__main__':
 parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8787); parser.add_argument('--data-dir'); parser.add_argument('--open-browser',action='store_true'); args=parser.parse_args()
 server=make_server(args.port,args.data_dir); print(f'LoveFlix is running at http://localhost:{server.server_port}',flush=True)
 if args.open_browser:
  import webbrowser
  threading.Timer(.5,lambda:webbrowser.open(f'http://localhost:{server.server_port}')).start()
 try: server.serve_forever()
 except KeyboardInterrupt: server.server_close()
