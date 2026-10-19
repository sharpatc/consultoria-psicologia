import sqlite3
import os
from contextlib import contextmanager
from pathlib import Path
from flask import current_app, g

def get_db_path():
    """Retrieve database path from current app config or fallback to env/default."""
    try:
        return current_app.config['DB_PATH']
    except (RuntimeError, KeyError):
        return os.environ.get('DB_PATH', 'database.sqlite')

def get_db_connection(db_path=None):
    """
    Get a standalone SQLite connection with Row factory enabled.
    Caller is responsible for closing this connection.
    """
    path = db_path or get_db_path()
    if not path.startswith('file:'):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, uri=path.startswith('file:'))
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA busy_timeout = 5000')
    conn.row_factory = sqlite3.Row
    return conn

def get_db():
    """
    Flask request-scoped database connection.
    Reuses connection on `g` during request and closes at request teardown.
    """
    if 'db' not in g:
        g.db = get_db_connection()
    return g.db

def close_db(e=None):
    """Closes request-scoped database connection if open."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

@contextmanager
def get_db_cursor(db_path=None):
    """
    Context manager for database transactions.
    Automatically commits on success and rolls back on exception.
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        yield cursor, conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
