"""Registration and single-use email recovery for shared LoveFlix accounts."""
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import ssl
import time
from email.message import EmailMessage
from urllib.parse import urlencode
from .errors import APIError

SCHEMA = [
 'CREATE TABLE IF NOT EXISTS account_details(user_id BIGINT PRIMARY KEY REFERENCES users(id),name TEXT NOT NULL,email TEXT NOT NULL UNIQUE,phone TEXT NOT NULL)',
 'CREATE TABLE IF NOT EXISTS password_resets(token TEXT PRIMARY KEY,user_id BIGINT NOT NULL REFERENCES users(id),expires DOUBLE PRECISION NOT NULL)',
 'CREATE TABLE IF NOT EXISTS account_sessions(token TEXT PRIMARY KEY,user_id BIGINT NOT NULL REFERENCES users(id))',
 'CREATE TABLE IF NOT EXISTS auth_requests(key TEXT PRIMARY KEY,started DOUBLE PRECISION NOT NULL,attempts INTEGER NOT NULL)',
]

def ensure_schema(db):
 for sql in SCHEMA: db.execute(sql)

def email_address(value):
 value=value.strip().lower()
 if len(value)>254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):
  raise APIError('Enter a valid email address.')
 return value

def digest(password,salt):
 return hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()

def password_value(handler,data):
 password=handler.text(data,'password',200,True)
 if len(password)<10: raise APIError('Use a password with at least 10 characters.')
 return password

def rate_limit(handler,action,identity,limit=10,window=300):
 key=hashlib.sha256((action+':'+identity).encode()).hexdigest();now=time.time()
 with handler.app.db() as db:
  row=db.execute('''INSERT INTO auth_requests(key,started,attempts) VALUES(?,?,1)
   ON CONFLICT(key) DO UPDATE SET
   attempts=CASE WHEN auth_requests.started<? THEN 1 ELSE auth_requests.attempts+1 END,
   started=CASE WHEN auth_requests.started<? THEN excluded.started ELSE auth_requests.started END
   RETURNING attempts''',(key,now,now-window,now-window)).fetchone()
 if row['attempts']>limit: raise APIError('Too many attempts. Please try again later.',429)

def mail_configured():
 return all(os.environ.get(x) for x in ['SMTP_HOST','SMTP_USER','SMTP_PASSWORD','SMTP_FROM','PUBLIC_ORIGIN'])

def send_reset(address,token):
 # The link origin comes only from trusted server configuration, never Host/input.
 origin=os.environ['PUBLIC_ORIGIN'].rstrip('/')
 if not origin.startswith('https://'): raise RuntimeError('An HTTPS public origin is required.')
 link=origin+'/login.html?mode=reset#'+urlencode({'token':token})
 message=EmailMessage();message['Subject']='Reset your LoveFlix password'
 message['From']=os.environ['SMTP_FROM'];message['To']=address
 message.set_content('You requested a LoveFlix password reset.\n\n'+link+'\n\nThis link expires in 30 minutes and can only be used once. If you did not request it, ignore this email.')
 port=int(os.environ.get('SMTP_PORT','587'))
 connection=smtplib.SMTP_SSL if port==465 else smtplib.SMTP
 with connection(os.environ['SMTP_HOST'],port,timeout=15,**({'context':ssl.create_default_context()} if port==465 else {})) as smtp:
  if port!=465: smtp.starttls(context=ssl.create_default_context())
  smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD']);smtp.send_message(message)

def handle(handler,path):
 data=handler.json_body()
 if path=='/api/accounts/change-password':
  if not handler.authorized(): raise APIError('Please log in again.',401)
  with handler.app.db() as db:
   user=db.execute('SELECT users.* FROM users JOIN account_sessions ON users.id=account_sessions.user_id WHERE account_sessions.token=?',(handler.token(),)).fetchone()
  if not user: raise APIError('Please sign out and log in again before changing your password.',403)
  rate_limit(handler,'change-password',str(user['id']),5,300)
  current=handler.text(data,'current_password',200,True)
  password=password_value(handler,data)
  if not hmac.compare_digest(digest(current,user['salt']),user['password']): raise APIError('Your current password is incorrect.',403)
  if password==current: raise APIError('Choose a different new password.')
  salt=secrets.token_hex(16);hashed=digest(password,salt)
  with handler.app.db() as db:
   updated=db.execute('UPDATE users SET salt=?,password=? WHERE id=? AND password=? RETURNING id',(salt,hashed,user['id'],user['password'])).fetchone()
   if not updated: raise APIError('Your password changed elsewhere. Please log in again.',403)
   db.execute('DELETE FROM password_resets WHERE user_id=?',(user['id'],))
   db.execute('DELETE FROM sessions WHERE token IN (SELECT token FROM account_sessions WHERE user_id=?)',(user['id'],))
   db.execute('DELETE FROM account_sessions WHERE user_id=?',(user['id'],))
  return handler.reply({'ok':True},cookie='lf_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
 if path.endswith('/register'):
  name=handler.text(data,'name',100,True).strip()
  email=email_address(handler.text(data,'email',254,True))
  phone=handler.text(data,'phone',30,True).strip()
  if not name: raise APIError('Enter your name.')
  if not re.fullmatch(r'\+?[0-9 ()-]{7,30}',phone) or not 7<=len(re.sub(r'\D','',phone))<=15: raise APIError('Enter a valid phone number, including your country code.')
  password=password_value(handler,data);rate_limit(handler,'register',handler.client_address[0],10,3600)
  salt=secrets.token_hex(16);hashed=digest(password,salt)
  with handler.app.db() as db:
   created=db.execute('INSERT INTO users(username,salt,password) VALUES(?,?,?) ON CONFLICT(username) DO NOTHING RETURNING id',(email,salt,hashed)).fetchone()
   if not created: raise APIError('An account already uses this email. Please log in or reset your password.',409)
   db.execute('INSERT INTO account_details(user_id,name,email,phone) VALUES(?,?,?,?)',(created['id'],name,email,phone))
  # Registration deliberately does not authenticate or issue a session cookie.
  return handler.reply({'ok':True})
 if path.endswith('/login'):
  identity=handler.text(data,'identity',254,True).strip()
  if '@' in identity: identity=identity.lower()
  password=handler.text(data,'password',200,True);rate_limit(handler,'login',identity)
  with handler.app.db() as db: user=db.execute('SELECT * FROM users WHERE username=?',(identity,)).fetchone()
  expected=digest(password,user['salt'] if user else '00'*16)
  if not user or not hmac.compare_digest(expected,user['password']): raise APIError('Email or password is incorrect.',401)
  cookie=handler.session(bool(data.get('remember')),user['id'])
  return handler.reply({'ok':True},cookie=cookie)
 if path.endswith('/forgot'):
  email=email_address(handler.text(data,'email',254,True))
  rate_limit(handler,'forgot-email',email,3,3600)
  rate_limit(handler,'forgot-ip',handler.client_address[0],20,3600)
  if not mail_configured(): raise APIError('Password-reset emails are not available yet. Please contact the site owner.',503)
  with handler.app.db() as db: user=db.execute('SELECT user_id FROM account_details WHERE email=?',(email,)).fetchone()
  if user:
   token=secrets.token_urlsafe(32);hashed=hashlib.sha256(token.encode()).hexdigest()
   with handler.app.db() as db: db.execute('INSERT INTO password_resets(token,user_id,expires) VALUES(?,?,?)',(hashed,user['user_id'],time.time()+1800))
   try: send_reset(email,token)
   except Exception:
    with handler.app.db() as db: db.execute('DELETE FROM password_resets WHERE token=?',(hashed,))
    # Keep the same public response for known and unknown emails; log no secrets.
    print('LoveFlix reset email delivery failed; check SMTP configuration.',flush=True)
  return handler.reply({'ok':True,'message':'If an account matches this email, a reset link will arrive shortly. Check your spam folder too.'})
 if path.endswith('/reset'):
  token=handler.text(data,'token',200,True);password=password_value(handler,data)
  rate_limit(handler,'reset',handler.client_address[0],10,300)
  hashed=hashlib.sha256(token.encode()).hexdigest();salt=secrets.token_hex(16);new_hash=digest(password,salt)
  with handler.app.db() as db:
   row=db.execute('DELETE FROM password_resets WHERE token=? AND expires>? RETURNING user_id',(hashed,time.time())).fetchone()
   if not row: raise APIError('This reset link has expired or was already used. Request a new one.',400)
   db.execute('UPDATE users SET salt=?,password=? WHERE id=?',(salt,new_hash,row['user_id']))
   db.execute('DELETE FROM password_resets WHERE user_id=?',(row['user_id'],))
   db.execute('DELETE FROM sessions WHERE token IN (SELECT token FROM account_sessions WHERE user_id=?)',(row['user_id'],))
   db.execute('DELETE FROM account_sessions WHERE user_id=?',(row['user_id'],))
  return handler.reply({'ok':True})
 raise APIError('Endpoint not found.',404)
