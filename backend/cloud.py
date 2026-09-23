"""Persistent Vercel backend. Secrets stay on the server; uploads bypass Functions."""
import hashlib
import json
import mimetypes
import os
import secrets
import threading
import time
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urlsplit
from .server import App, Handler, APIError, COLLECTIONS, MAX_UPLOAD

class Row(dict):
    def __getitem__(self, key):
        return list(self.values())[key] if isinstance(key, int) else super().__getitem__(key)

def row_factory(cursor):
    names = [column.name for column in cursor.description] if cursor.description else []
    return lambda values: Row(zip(names, values))

class Database:
    """Translate the two SQLite upserts used by the shared request handlers."""
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, params=()):
        sql = sql.replace('?', '%s').replace('kind="photo"', "kind='photo'")
        if sql.startswith('INSERT OR REPLACE INTO favorites'):
            sql = sql.replace('INSERT OR REPLACE', 'INSERT') + ' ON CONFLICT(profile,id) DO UPDATE SET value=excluded.value'
        elif sql.startswith('INSERT OR REPLACE INTO content'):
            sql = sql.replace('INSERT OR REPLACE', 'INSERT') + ' ON CONFLICT(page,selector) DO UPDATE SET text=excluded.text'
        return self.connection.execute(sql, params)

class CloudApp(App):
    def __init__(self):
        required = ['DATABASE_URL', 'S3_ENDPOINT_URL', 'S3_REGION', 'S3_ACCESS_KEY_ID', 'S3_SECRET_ACCESS_KEY', 'S3_BUCKET']
        if any(not os.environ.get(key) for key in required):
            raise RuntimeError('Cloud storage is not configured.')
        import boto3
        from botocore.config import Config
        self.lock = threading.Lock()
        self.attempts = {}
        self.bucket = os.environ['S3_BUCKET']
        self.storage = boto3.client('s3', endpoint_url=os.environ['S3_ENDPOINT_URL'], region_name=os.environ['S3_REGION'],
            aws_access_key_id=os.environ['S3_ACCESS_KEY_ID'], aws_secret_access_key=os.environ['S3_SECRET_ACCESS_KEY'],
            config=Config(signature_version='s3v4', s3={'addressing_style':'path'}, request_checksum_calculation='when_required', response_checksum_validation='when_required'))

        from .accounts import ensure_schema
        with self.db() as db:
            ensure_schema(db)

    @contextmanager
    def db(self):
        import psycopg
        # Transaction pooling requires prepared statements to be disabled.
        with psycopg.connect(os.environ['DATABASE_URL'], sslmode='require', prepare_threshold=None,
                             connect_timeout=10, row_factory=row_factory) as connection:
            connection.execute('SET LOCAL search_path TO loveflix')
            yield Database(connection)

    def media(self, row):
        result = super().media(row)
        result['displayUrl'] = self.signed_read(row['path']) if not row['deleted'] else ''
        return result

    def signed_read(self, path):
        # Reuse URLs long enough for browser caching, well inside their expiry.
        return self._signed_read(path, int(time.time() // 900))

    @lru_cache(maxsize=2048)
    def _signed_read(self, path, window):
        return self.storage.generate_presigned_url('get_object', Params={'Bucket':self.bucket,'Key':path}, ExpiresIn=3600)

@lru_cache(maxsize=1)
def cloud_app():
    return CloudApp()

class CloudHandler(Handler):
    @property
    def app(self):
        return cloud_app()

    @property
    def public_origin(self):
        explicit = os.environ.get('PUBLIC_ORIGIN', '').rstrip('/')
        host = os.environ.get('VERCEL_PROJECT_PRODUCTION_URL') or os.environ.get('VERCEL_URL')
        return explicit or ('https://' + host if host else '')

    def protect(self, mutation=False):
        origins = {self.public_origin}
        preview = os.environ.get('VERCEL_URL')
        if preview:
            origins.add('https://' + preview)
        origins.discard('')
        host = self.headers.get('Host', '')
        expected = 'https://' + host
        if expected not in origins:
            raise APIError('Invalid host.', 403)
        if mutation and (self.headers.get('Origin', expected) != expected or self.headers.get('Sec-Fetch-Site') == 'cross-site'):
            raise APIError('Cross-site requests are not allowed.', 403)

    def dispatch(self, method):
        try:
            self.protect(method not in ['GET','HEAD'])
            self.route(method)
        except APIError as error:
            self.reply({'error':str(error)}, error.status)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            # Connection exceptions may contain credentials; do not log their text.
            self.reply({'error':'The online service is not ready. Please try again shortly.'}, 503)

    def log_message(self, format, *args):
        pass

    def route(self, method):
        path = unquote(urlsplit(self.path).path)
        if path == '/healthz':
            with self.app.db() as db:
                db.execute('SELECT 1 FROM settings LIMIT 1').fetchone()
            return self.reply({'ok':True})
        if path in ['/api/setup', '/api/register', '/api/login'] and method == 'POST':
            return self.authenticate(path)
        if path in ['/api/uploads/prepare','/api/uploads/complete'] and method == 'POST':
            if not self.authorized():
                raise APIError('Please sign in.', 401)
            return self.prepare_upload() if path.endswith('prepare') else self.complete_upload()
        if path == '/api/state' and method == 'GET':
            if not self.authorized():
                raise APIError('Please sign in.',401)
            state = self.app.state()
            state['directUploads'] = True
            return self.reply(state)
        if path.startswith('/media/') and method in ['GET','HEAD']:
            if not self.authorized():
                raise APIError('Please sign in.',401)
            with self.app.db() as db:
                row = db.execute('SELECT path FROM media WHERE id=? AND deleted=0',(path.split('/')[-1],)).fetchone()
            if not row:
                raise APIError('Media not found.',404)
            return self.redirect_media(row['path'])
        if path.startswith(('/images/','/videos/')) or (path.startswith('/play/') and Path(path).suffix.lower() in ['.mp4','.mov','.webm']) or path == '/birthday.mp4':
            if not self.authorized():
                raise APIError('Please sign in.',401)
            with self.app.db() as db:
                row = db.execute('SELECT path FROM media WHERE original=? AND deleted=0',(path.lstrip('/'),)).fetchone()
            if not row:
                raise APIError('Media not found.',404)
            return self.redirect_media(row['path'])
        return super().route(method)

    def redirect_media(self, path):
        self.send_response(307)
        self.headers_common()
        self.send_header('Location', self.app.signed_read(path))
        self.send_header('Content-Length','0')
        self.end_headers()

    def authenticate(self, path):
        data = self.json_body()
        username = self.text(data,'username',80,True)
        password = self.text(data,'password',200,True)
        # Shared database rate limit works across serverless instances.
        key = hashlib.sha256(username.encode()).hexdigest()
        with self.app.db() as db:
            record = db.execute('''INSERT INTO login_attempts(key,started,attempts) VALUES(?,?,1)
                ON CONFLICT(key) DO UPDATE SET
                attempts=CASE WHEN login_attempts.started<? THEN 1 ELSE login_attempts.attempts+1 END,
                started=CASE WHEN login_attempts.started<? THEN excluded.started ELSE login_attempts.started END
                RETURNING attempts''',(key,time.time(),time.time()-300,time.time()-300)).fetchone()
        if record['attempts'] > 10:
            raise APIError('Too many attempts. Try again in five minutes.',429)
        if path in ['/api/setup','/api/register']:
            if len(password)<10:
                raise APIError('Use a password with at least 10 characters.')
            salt = secrets.token_hex(16)
            digest = hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
            with self.app.db() as db:
                db.execute('SELECT pg_advisory_xact_lock(745301)')
                if path == '/api/setup' and db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                    raise APIError('Your account already exists. Please sign in.',409)
                row=db.execute('INSERT INTO users(username,salt,password) VALUES(?,?,?) ON CONFLICT(username) DO NOTHING RETURNING id',(username,salt,digest)).fetchone()
                if not row:
                    raise APIError('This username is taken. Choose another one.',409)
        else:
            import hmac
            with self.app.db() as db:
                user=db.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
            salt = user['salt'] if user else '00'*16
            digest=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
            if not user or not hmac.compare_digest(digest,user['password']):
                raise APIError('Username or password is incorrect.',401)
        with self.app.db() as db:
            db.execute('DELETE FROM login_attempts WHERE key=?',(key,))
        with self.app.db() as db:
            account=db.execute('SELECT id FROM users WHERE username=?',(username,)).fetchone()
        return self.reply({'ok':True},cookie=self.session(bool(data.get('remember')),account['id']))

    def upload(self, mid=None):
        raise APIError('Refresh the page to enable direct uploads.',400)

    def prepare_upload(self):
        data=self.json_body()
        name=self.text(data,'name',200,True)
        group=self.text(data,'collection',40,True)
        mid=self.text(data,'id',100) or None
        size=data.get('size')
        ext=Path(name).suffix.lower()
        if type(size) is not int or not 0<size<=MAX_UPLOAD:
            raise APIError('Choose a file up to 250 MB.')
        if ext not in ['.jpg','.jpeg','.png','.webp','.gif','.mp4','.webm','.mov'] or group not in COLLECTIONS+['profile']:
            raise APIError('Choose a supported file and album.')
        kind='video' if ext in ['.mp4','.webm','.mov'] else 'photo'
        if (group in ['videos','surprise'] and kind!='video') or (group=='profile' and kind!='photo'):
            raise APIError('Choose the correct file type for this album.')
        if group=='play' and not mid:
            raise APIError('Use Replace file on the Play movie.')
        with self.app.db() as db:
            if mid:
                row=db.execute('SELECT kind FROM media WHERE id=?',(mid,)).fetchone()
                if not row or row['kind']!=kind:
                    raise APIError('Choose a matching replacement file.')
            upload_id=secrets.token_hex(20)
            key='pending/'+upload_id+ext
            content_type=mimetypes.guess_type(name)[0] or 'application/octet-stream'
            db.execute('INSERT INTO pending_uploads(id,token,path,name,kind,collection,media_id,size,expires) VALUES(?,?,?,?,?,?,?,?,?)',
                       (upload_id,self.token(),key,name,kind,group,mid,size,time.time()+3600))
        url=self.app.storage.generate_presigned_url('put_object',Params={'Bucket':self.app.bucket,'Key':key,'ContentType':content_type,'ContentLength':size},ExpiresIn=3600)
        return self.reply({'id':upload_id,'url':url,'contentType':content_type})

    def complete_upload(self):
        data=self.json_body()
        upload_id=self.text(data,'id',100,True)
        with self.app.db() as db:
            row=db.execute('SELECT * FROM pending_uploads WHERE id=? AND token=? AND expires>? FOR UPDATE',(upload_id,self.token(),time.time())).fetchone()
            if not row:
                raise APIError('This upload expired or was already saved.',409)
            ext=Path(row['name']).suffix.lower()
            # Copy to a key the browser cannot overwrite with its still-valid upload URL.
            final_key='uploads/'+upload_id+ext
            self.app.storage.copy_object(Bucket=self.app.bucket,Key=final_key,CopySource={'Bucket':self.app.bucket,'Key':row['path']})
            metadata=self.app.storage.head_object(Bucket=self.app.bucket,Key=final_key)
            if metadata['ContentLength']!=row['size']:
                raise APIError('Upload size does not match. Please upload again.')
            response=self.app.storage.get_object(Bucket=self.app.bucket,Key=final_key,Range='bytes=0-31')
            try: head=response['Body'].read(32)
            finally: response['Body'].close()
            ext=Path(row['name']).suffix.lower()
            valid=(ext in ['.jpg','.jpeg'] and head.startswith(b'\xff\xd8\xff')) or (ext=='.png' and head.startswith(b'\x89PNG\r\n\x1a\n')) or (ext=='.gif' and head[:6] in [b'GIF87a',b'GIF89a']) or (ext=='.webp' and head[:4]==b'RIFF' and head[8:12]==b'WEBP') or (ext in ['.mp4','.mov'] and b'ftyp' in head) or (ext=='.webm' and head.startswith(b'\x1aE\xdf\xa3'))
            if not valid:
                raise APIError('This file does not match its media type.')
            mid=row['media_id'] or secrets.token_hex(12)
            if row['media_id']:
                db.execute('UPDATE media SET path=?,revision=revision+1 WHERE id=?',(final_key,mid))
            else:
                db.execute('INSERT INTO media(id,original,path,kind,title,collections,created) VALUES(?,?,?,?,?,?,?)',
                           (mid,'',final_key,row['kind'],Path(row['name']).stem[:200],json.dumps([] if row['collection']=='profile' else [row['collection']]),time.time()))
            result=db.execute('SELECT * FROM media WHERE id=?',(mid,)).fetchone()
            db.execute('DELETE FROM pending_uploads WHERE id=?',(upload_id,))
        return self.reply(self.app.media(result),201)
