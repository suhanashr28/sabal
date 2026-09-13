"""Initialize an empty cloud installation and copy media to its private bucket.
Run locally with the six documented environment variables. Never run at build time.
"""
import argparse
import json
import mimetypes
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.server import App, ROOT
from backend.cloud import CloudApp

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--local-data',type=Path,help='Explicitly copy accounts and saved changes from this local data directory.')
    args=parser.parse_args()
    import psycopg
    app=CloudApp()
    # The bucket must be created as PRIVATE in Supabase before running this script.
    app.storage.head_bucket(Bucket=app.bucket)
    with psycopg.connect(os.environ['DATABASE_URL'],sslmode='require',prepare_threshold=None) as connection:
        connection.execute('SELECT pg_advisory_xact_lock(745300)')
        for statement in (ROOT/'backend/cloud_schema.sql').read_text().split(';'):
            if statement.strip(): connection.execute(statement)
        if connection.execute('SELECT count(*) FROM media').fetchone()[0]:
            print('Cloud media is already initialized; saved data was left unchanged.')
            return
        with tempfile.TemporaryDirectory() as temp:
            if args.local_data:
                data=args.local_data.resolve()
                database=data/'loveflix.sqlite3'
                if not database.is_file(): raise ValueError('The selected local database does not exist.')
            else:
                data=Path(temp)
                App(data)
                database=data/'loveflix.sqlite3'
            source=sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)
            source.row_factory=sqlite3.Row
            try:
                source.execute('BEGIN')
                media=source.execute('SELECT * FROM media').fetchall()
                for row in media:
                    relative=row['path']
                    base=data if relative.startswith('uploads/') else ROOT
                    file=(base/relative).resolve()
                    if not file.is_relative_to(base) or not file.is_file():
                        raise ValueError('A media file is missing; initialization was cancelled.')
                    app.storage.upload_file(str(file),app.bucket,relative,ExtraArgs={'ContentType':mimetypes.guess_type(file.name)[0] or 'application/octet-stream'})
                for table in ['users','settings','profiles','media','favorites','content']:
                    rows=source.execute('SELECT * FROM '+table).fetchall()
                    for row in rows:
                        columns=list(row.keys())
                        placeholders=','.join(['%s']*len(columns))
                        connection.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})",tuple(row))
                connection.execute("SELECT setval(pg_get_serial_sequence('loveflix.users','id'),COALESCE((SELECT max(id) FROM users),1),EXISTS(SELECT 1 FROM users))")
            finally: source.close()
    print('Cloud database and media initialized. Sessions were not copied; sign in again online.')

if __name__=='__main__':
    try: main()
    except Exception:
        # SDK/connection exceptions can embed secret credentials or signed URLs.
        print('Setup failed. Check your connection settings, private bucket, quota, and local media files. No database changes were committed.',file=sys.stderr)
        sys.exit(1)
