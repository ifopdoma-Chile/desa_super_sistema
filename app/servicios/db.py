import os
import logging
import psycopg2
import psycopg2.pool
import psycopg2.extras
from psycopg2.extras import RealDictCursor, execute_values
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_pool = None


def _conn_kwargs():
    return dict(
        host=os.environ.get("HDO_DB_HOST", "localhost"),
        port=int(os.environ.get("HDO_DB_PORT", 5432)),
        dbname=os.environ.get("HDO_DB_NAME", "hdo"),
        user=os.environ.get("HDO_DB_USER", "postgres"),
        password=os.environ.get("HDO_DB_PASS", ""),
        connect_timeout=10,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )


def get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2, maxconn=10, **_conn_kwargs()
        )
    return _pool


def _is_alive(conn) -> bool:
    """Real liveness check: a conn.closed=False socket may still be dead
    (server-side close / CLOSE-WAIT). A cheap SELECT 1 detects it."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    except Exception:
        return False


def _get_valid_conn():
    """Get a live connection from the pool. If the pool hands back a stale
    connection (server-side close / CLOSE-WAIT), discard it (key=None) and
    ask the pool again — the pool will create a fresh managed connection.
    Falls back to a direct connection only if the pool is exhausted."""
    pool = get_pool()
    for _ in range(3):
        conn = pool.getconn()
        if conn.closed or not _is_alive(conn):
            logger.warning("Stale connection from pool (host=%s), discarding...", _conn_kwargs()["host"])
            try:
                pool.putconn(conn, key=None)  # remove broken conn from pool
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
            continue  # ask the pool again (it will create a fresh one)
        return conn
    # Pool exhausted with only stale conns: fall back to a direct connection
    logger.warning("Pool returned only stale connections, opening direct connection...")
    return psycopg2.connect(**_conn_kwargs())


@contextmanager
def get_db():
    pool = get_pool()
    conn = _get_valid_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        # Broken connection: discard instead of returning to pool
        try:
            pool.putconn(conn, key=None)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
        raise
    finally:
        try:
            pool.putconn(conn)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass


def _retry_once(exc: Exception) -> bool:
    """Log and rebuild pool for transient connection errors (SSL closed,
    connection reset, etc.). Returns True when a retry is worthwhile."""
    msg = str(exc).lower()
    if isinstance(exc, psycopg2.OperationalError) or "ssl" in msg or "closed" in msg or "reset" in msg:
        logger.warning("DB connection error (%s), rebuilding pool and retrying once...", exc)
        try:
            _pool.closeall()  # drop all stale conns; pool will lazily recreate
        except Exception:
            pass
        return True
    return False


def query(sql, params=None, fetch=True):
    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                if fetch:
                    return cur.fetchall()
                return None
    except Exception as exc:
        if _retry_once(exc):
            with get_db() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, params)
                    if fetch:
                        return cur.fetchall()
                    return None
        raise


def insert_many(table, columns, rows):
    sql = "INSERT INTO hdo." + table + " (" + ",".join(columns) + ") VALUES %s ON CONFLICT DO NOTHING"
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                execute_values(cur, sql, rows)
                conn.commit()
                return len(rows)
    except Exception as exc:
        if _retry_once(exc):
            with get_db() as conn:
                with conn.cursor() as cur:
                    execute_values(cur, sql, rows)
                    conn.commit()
                    return len(rows)
        raise
