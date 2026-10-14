import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import closing

LOGGER = logging.getLogger(__name__)

class SQLiteStorageProvider:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        # Enable WAL mode for better concurrency and foreign keys
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._get_conn()) as conn, conn:
            # Main memory table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    assistant_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    active INTEGER DEFAULT 1,
                    metadata TEXT
                )
            """)
            
            # FTS5 search table
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    id UNINDEXED,
                    content,
                    tokenize='unicode61'
                )
            """)

            # Triggers to keep FTS5 in sync with memories table
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories
                BEGIN
                    INSERT INTO memories_fts (id, content)
                    VALUES (new.id, new.content);
                END;
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories
                BEGIN
                    DELETE FROM memories_fts WHERE id = old.id;
                END;
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories
                BEGIN
                    DELETE FROM memories_fts WHERE id = old.id;
                    INSERT INTO memories_fts (id, content)
                    VALUES (new.id, new.content);
                END;
            """)
            
            conn.commit()

    def store(self, mem_id: str, content: str, category: str, scope: str, assistant_id: str, source: str, confidence: float, created_at: str, updated_at: str, active: int, metadata: str):
        with closing(self._get_conn()) as conn, conn:
            conn.execute("""
                INSERT INTO memories (id, content, category, scope, assistant_id, source, confidence, created_at, updated_at, active, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content=excluded.content,
                    category=excluded.category,
                    scope=excluded.scope,
                    assistant_id=excluded.assistant_id,
                    source=excluded.source,
                    confidence=excluded.confidence,
                    updated_at=excluded.updated_at,
                    active=excluded.active,
                    metadata=excluded.metadata
            """, (mem_id, content, category, scope, assistant_id, source, confidence, created_at, updated_at, active, metadata))
            conn.commit()

    def deactivate(self, mem_id: str, updated_at: str):
        with closing(self._get_conn()) as conn, conn:
            conn.execute("UPDATE memories SET active=0, updated_at=? WHERE id=?", (updated_at, mem_id))
            conn.commit()

    def get_all_active(self, scope: str = None, assistant_id: str = None) -> List[sqlite3.Row]:
        with closing(self._get_conn()) as conn, conn:
            query = "SELECT * FROM memories WHERE active=1"
            params = []
            
            if scope:
                query += " AND scope=?"
                params.append(scope)
            if assistant_id:
                query += " AND assistant_id=?"
                params.append(assistant_id)
                
            query += " ORDER BY updated_at DESC"
            return conn.execute(query, params).fetchall()

    def search_fts(self, query: str, scope: str = None, assistant_id: str = None, limit: int = 5) -> List[sqlite3.Row]:
        with closing(self._get_conn()) as conn, conn:
            # We join FTS5 with main table to filter on active, scope, assistant_id
            sql = """
                SELECT m.*, f.rank 
                FROM memories_fts f
                JOIN memories m ON f.id = m.id
                WHERE f.content MATCH ? AND m.active=1
            """
            params = [query]
            
            if scope and assistant_id:
                # E.g. (scope='GLOBAL' OR assistant_id='jarvis')
                sql += " AND (m.scope='global' OR m.assistant_id=?)"
                params.append(assistant_id)
            elif assistant_id:
                sql += " AND m.assistant_id=?"
                params.append(assistant_id)
            elif scope:
                sql += " AND m.scope=?"
                params.append(scope)
                
            sql += " ORDER BY f.rank LIMIT ?"
            params.append(limit)
            
            try:
                return conn.execute(sql, params).fetchall()
            except sqlite3.OperationalError as e:
                # FTS queries might be malformed if they contain specific characters
                LOGGER.warning(f"FTS search failed for query '{query}': {e}")
                return []

    def get_by_id(self, mem_id: str) -> Optional[sqlite3.Row]:
        with closing(self._get_conn()) as conn, conn:
            row = conn.execute("SELECT * FROM memories WHERE id=?", (mem_id,)).fetchone()
            return row
