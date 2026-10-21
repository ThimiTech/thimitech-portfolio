"""Dev helper used by start.bat / start.sh (run from backend/).

    python dev_check.py db     -> ensure the PostgreSQL database named in .env exists.
                                  exit 0 = exists, 3 = just created (fresh), 1 = error
    python dev_check.py redis  -> exit 0 if the Celery broker (Redis) answers PING, else 1
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def check_db():
    import psycopg2
    from psycopg2 import sql

    name = os.getenv('DB_NAME') or 'thimitech'
    params = {
        'user': os.getenv('DB_USER') or 'postgres',
        'password': os.getenv('DB_PASSWORD') or '',
        'host': os.getenv('DB_HOST') or 'localhost',
        'port': os.getenv('DB_PORT') or '5432',
    }
    try:
        conn = psycopg2.connect(dbname='postgres', connect_timeout=5, **params)
    except psycopg2.Error as e:
        print(f"[db] Cannot connect to PostgreSQL at {params['host']}:{params['port']} as {params['user']}: {str(e).strip()}")
        print('[db] Check DB_* in backend/.env and that PostgreSQL 15+ is running.')
        return 1

    conn.autocommit = True
    try:
        if conn.server_version < 150000:
            print(f'[db] PostgreSQL {conn.server_version // 10000} found on port {params["port"]}; '
                  'Django 6 needs 15+. Point DB_PORT in backend/.env at a newer server.')
            return 1
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM pg_database WHERE datname = %s', [name])
            if cur.fetchone():
                return 0
            cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        print(f'[db] Created database "{name}".')
        return 3
    finally:
        conn.close()


def check_redis():
    import redis

    url = os.getenv('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    try:
        redis.from_url(url, socket_connect_timeout=1).ping()
        return 0
    except Exception:
        return 1


if __name__ == '__main__':
    checks = {'db': check_db, 'redis': check_redis}
    if len(sys.argv) != 2 or sys.argv[1] not in checks:
        print(__doc__)
        sys.exit(2)
    sys.exit(checks[sys.argv[1]]())
