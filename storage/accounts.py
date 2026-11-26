"""Repository layer: no encryption logic and no Telegram imports here."""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite

from storage.database import Database


@dataclass(frozen=True)
class StoredAccount:
    login: str
    encrypted_data: str


class AccountRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def list_logins(self) -> list[str]:
        async with aiosqlite.connect(self._db.path) as db:
            cursor = await db.execute("SELECT login FROM accounts ORDER BY login COLLATE NOCASE")
            rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def get(self, login: str) -> StoredAccount | None:
        async with aiosqlite.connect(self._db.path) as db:
            cursor = await db.execute(
                "SELECT login, encrypted_data FROM accounts WHERE login = ? COLLATE NOCASE",
                (login,),
            )
            row = await cursor.fetchone()
        return StoredAccount(login=row[0], encrypted_data=row[1]) if row else None

    async def upsert(self, login: str, encrypted_data: str) -> None:
        async with aiosqlite.connect(self._db.path) as db:
            await db.execute(
                """
                INSERT INTO accounts (login, encrypted_data, updated_at)
                VALUES (?, ?, datetime('now'))
                ON CONFLICT(login) DO UPDATE SET
                    encrypted_data = excluded.encrypted_data,
                    updated_at = datetime('now')
                """,
                (login, encrypted_data),
            )
            await db.commit()

    async def delete(self, login: str) -> bool:
        async with aiosqlite.connect(self._db.path) as db:
            cursor = await db.execute(
                "DELETE FROM accounts WHERE login = ? COLLATE NOCASE", (login,)
            )
            await db.commit()
            return cursor.rowcount > 0
