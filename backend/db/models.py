import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "taste_toronto.db"

CREATE_RESTAURANTS = """
CREATE TABLE IF NOT EXISTS restaurants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT,
    neighborhood TEXT,
    cuisine TEXT,
    price_range TEXT,
    rating REAL,
    review_count INTEGER,
    phone TEXT,
    website TEXT,
    reservation_url TEXT,
    noise_level TEXT,
    parking INTEGER,
    semantic_tags TEXT,
    occasion_scores TEXT,
    description TEXT,
    google_place_id TEXT,
    latitude REAL,
    longitude REAL,
    photo_name TEXT,
    created_at TEXT DEFAULT (datetime('now'))
)
"""

CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    created_at TEXT DEFAULT (datetime('now')),
    last_active TEXT DEFAULT (datetime('now')),
    message_count INTEGER DEFAULT 0
)
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(CREATE_RESTAURANTS)
        conn.execute(CREATE_SESSIONS)
        _migrate(conn)
        conn.commit()


def _migrate(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(restaurants)").fetchall()}
    for col, typedef in [
        ("google_place_id", "TEXT"),
        ("latitude", "REAL"),
        ("longitude", "REAL"),
        ("photo_name", "TEXT"),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE restaurants ADD COLUMN {col} {typedef}")
