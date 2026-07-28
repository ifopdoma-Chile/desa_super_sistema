import os
import psycopg2
import psycopg2.pool
import psycopg2.extras
from psycopg2.extras import RealDictCursor, execute_values
from contextlib import contextmanager

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2, maxconn=10,
            host=os.environ.get("HDO_DB_HOST", "localhost"),
            port=int(os.environ.get("HDO_DB_PORT", 5432)),
            dbname=os.environ.get("HDO_DB_NAME", "hdo"),
            user=os.environ.get("HDO_DB_USER", "postgres"),
            password=os.environ.get("HDO_DB_PASS", "")
        )
    return _pool

@contextmanager
def get_db():
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)

def query(sql, params=None, fetch=True):
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch:
                return cur.fetchall()
            return None

def insert_many(table, columns, rows):
    sql = "INSERT INTO hdo." + table + " (" + ",".join(columns) + ") VALUES %s ON CONFLICT DO NOTHING"
    with get_db() as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)
            conn.commit()
            return len(rows)
