import sqlite3
import os
from contextlib import contextmanager
from app.config import Config

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS visitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    secondary_identifier TEXT NOT NULL,
    pin TEXT NOT NULL,
    visit_count INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_visit_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, secondary_identifier)
);

CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    visitor_id INTEGER NOT NULL,
    filename TEXT NOT NULL UNIQUE,
    original_filename TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    consent_display INTEGER NOT NULL DEFAULT 1,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    visit_number INTEGER NOT NULL DEFAULT 1,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(visitor_id) REFERENCES visitors(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_visitors_lookup ON visitors(name, secondary_identifier);
CREATE INDEX IF NOT EXISTS idx_photos_visitor ON photos(visitor_id);
CREATE INDEX IF NOT EXISTS idx_photos_display ON photos(consent_display, is_deleted);
"""

def get_db_connection(db_path=None):
    """Create a thread-safe connection configured with WAL mode and busy timeout."""
    path = db_path or Config.DATABASE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    # Configure SQLite for high concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

@contextmanager
def db_session(db_path=None):
    """Context manager for safe database transactions with auto-commit and rollback."""
    conn = get_db_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(db_path=None):
    """Initialize database tables and indexes."""
    Config.ensure_directories()
    with db_session(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
