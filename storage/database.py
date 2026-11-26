"""SQLite storage. Only encrypted blobs and plain account logins are stored."""

from __future__ import annotations

import os
from pathlib import Path

import aiosqlite


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.path.parent, 0o700)
        except OSError:
            pass
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    encrypted_data TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            await db.commit()
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
