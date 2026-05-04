import sqlite3
from datetime import date
from tanren.config import DB_FILE, ensure_data_dir

def get_connection() -> sqlite3.Connection:
    ensure_data_dir()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection):
    try:
        conn.execute("ALTER TABLE skills ADD COLUMN major_category TEXT DEFAULT '実装力'")
        conn.commit()
    except Exception:
        pass

def init_db():
    conn = get_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS checkins (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                date         DATE NOT NULL,
                work_summary TEXT,
                learnings    TEXT,
                blockers     TEXT,
                energy_level INTEGER,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS goals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                description TEXT,
                category    TEXT DEFAULT 'technical',
                target_date DATE,
                status      TEXT DEFAULT 'active',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS goal_notes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id    INTEGER REFERENCES goals(id),
                note       TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS skills (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                category   TEXT,
                level      INTEGER,
                notes      TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS skill_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id    INTEGER REFERENCES skills(id),
                level       INTEGER,
                notes       TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                command       TEXT,
                prompt        TEXT,
                response      TEXT,
                input_tokens  INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cached_tokens INTEGER DEFAULT 0,
                cost_usd      REAL DEFAULT 0,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS budget_usage (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                year_month    TEXT NOT NULL UNIQUE,
                input_tokens  INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cached_tokens INTEGER DEFAULT 0,
                cost_usd      REAL DEFAULT 0,
                updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS summaries (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                type           TEXT,
                period         TEXT,
                content        TEXT,
                original_count INTEGER,
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    conn.close()


def has_checkin_today() -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM checkins WHERE date = ?", (date.today().isoformat(),)
    ).fetchone()
    conn.close()
    return row is not None
