import sqlite3
from pathlib import Path
from app.config import DB_PATH, logger

def get_connection() -> sqlite3.Connection:
    """Establish and return a connection to the SQLite database."""
    # Ensure the parent directory (e.g., 'data/') exists
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Initialize the SQLite schema."""
    logger.info("Initializing database schema...")
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS release_note_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT,
                published_date TEXT,
                raw_text TEXT,
                source_url TEXT,
                doc_links TEXT,
                event_hash TEXT UNIQUE NOT NULL,
                rule_score REAL DEFAULT 0.0,
                popularity_score REAL DEFAULT 0.0,
                final_score REAL DEFAULT 0.0,
                ai_processed BOOLEAN DEFAULT 0,
                ai_relevance TEXT,
                ai_summary TEXT,
                category TEXT,
                published_week TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    logger.info("Database schema initialized.")