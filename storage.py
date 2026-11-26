"""
Local SQLite database for storing transcription history and metadata.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import DB_PATH

logger = logging.getLogger(__name__)


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the SQLite database tables and indices."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transcriptions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                uploader TEXT,
                source_type TEXT DEFAULT 'youtube',
                url TEXT,
                duration REAL DEFAULT 0,
                thumbnail TEXT,
                model_used TEXT,
                language TEXT,
                full_text TEXT,
                segments_json TEXT,
                audio_path TEXT,
                summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transcriptions_created ON transcriptions(created_at DESC)")
        conn.commit()


def save_transcription(data: Dict[str, Any]) -> str:
    """Inserts or replaces a transcription record."""
    init_db()
    trans_id = str(data["id"])
    segments_json = json.dumps(data.get("segments", []), ensure_ascii=False)

    with get_db_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO transcriptions (
                id, title, uploader, source_type, url, duration,
                thumbnail, model_used, language, full_text,
                segments_json, audio_path, summary, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trans_id,
            data.get("title", "Untitled Transcription"),
            data.get("uploader", "Unknown"),
            data.get("source_type", "youtube"),
            data.get("url", ""),
            float(data.get("duration", 0)),
            data.get("thumbnail", ""),
            data.get("model_used", "base"),
            data.get("language", "auto"),
            data.get("full_text", ""),
            segments_json,
            data.get("audio_path", ""),
            data.get("summary", ""),
            datetime.now().isoformat()
        ))
        conn.commit()
    return trans_id


def list_transcriptions(search_query: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Lists recent transcriptions without the heavy segments blob."""
    init_db()
    with get_db_connection() as conn:
        if search_query and search_query.strip():
            like_term = f"%{search_query.strip()}%"
            cursor = conn.execute("""
                SELECT id, title, uploader, source_type, url, duration,
                       thumbnail, model_used, language, summary, created_at,
                       SUBSTR(full_text, 1, 200) as preview_text
                FROM transcriptions
                WHERE title LIKE ? OR full_text LIKE ? OR uploader LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (like_term, like_term, like_term, limit))
        else:
            cursor = conn.execute("""
                SELECT id, title, uploader, source_type, url, duration,
                       thumbnail, model_used, language, summary, created_at,
                       SUBSTR(full_text, 1, 200) as preview_text
                FROM transcriptions
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_transcription(trans_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves full transcription details by ID."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.execute("""
            SELECT * FROM transcriptions WHERE id = ?
        """, (trans_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        data = dict(row)
        try:
            data["segments"] = json.loads(data.get("segments_json") or "[]")
        except Exception:
            data["segments"] = []
        data.pop("segments_json", None)
        return data


def delete_transcription(trans_id: str) -> bool:
    """Deletes a transcription by ID."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM transcriptions WHERE id = ?", (trans_id,))
        conn.commit()
        return cursor.rowcount > 0
