from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from config import MEMORY_DB, ensure_directories
from utils.logger import LOGGER


class MemoryStore:
    """Small persistent memory layer for preferences, events, and conversations."""

    def __init__(self, db_path: Path = MEMORY_DB) -> None:
        ensure_directories()
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )

    def remember(self, key: str, value: Any) -> None:
        normalized_key = key.strip().lower()
        payload = json.dumps(value, ensure_ascii=False)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO preferences(key, value, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (normalized_key, payload, time.time()),
            )
        LOGGER.info("Memory saved: %s", normalized_key)

    def recall(self, key: str) -> Any | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM preferences WHERE key = ?", (key.strip().lower(),)
            ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["value"])
        except json.JSONDecodeError:
            return row["value"]

    def search_preferences(self, query: str) -> list[tuple[str, Any]]:
        like = f"%{query.strip().lower()}%"
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value FROM preferences WHERE key LIKE ? ORDER BY updated_at DESC",
                (like,),
            ).fetchall()
        result: list[tuple[str, Any]] = []
        for row in rows:
            try:
                value = json.loads(row["value"])
            except json.JSONDecodeError:
                value = row["value"]
            result.append((row["key"], value))
        return result

    def add_message(self, role: str, content: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations(role, content, created_at) VALUES(?, ?, ?)",
                (role, content, time.time()),
            )

    def recent_messages(self, limit: int = 16) -> list[dict[str, str]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    def log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO events(type, payload, created_at) VALUES(?, ?, ?)",
                (event_type, json.dumps(payload, ensure_ascii=False), time.time()),
            )
