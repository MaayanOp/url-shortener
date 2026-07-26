"""
Storage layer for the URL shortener.

Defines an abstract interface so the service layer doesn't care whether
data lives in memory or in a real database. This is the classic
"program to an interface, not an implementation" OOP principle, and it
means swapping storage backends (e.g. moving from SQLite to Postgres or
DynamoDB) requires no changes to the business logic in shortener.py.
"""

from abc import ABC, abstractmethod
from typing import Optional
import sqlite3
import threading


class URLStorage(ABC):
    """Abstract interface every storage backend must implement."""

    @abstractmethod
    def save(self, short_code: str, long_url: str) -> None:
        """Persist a mapping from short_code to long_url."""
        raise NotImplementedError

    @abstractmethod
    def get(self, short_code: str) -> Optional[str]:
        """Return the long_url for a short_code, or None if not found."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, short_code: str) -> bool:
        """Check whether a short_code is already in use."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Return the total number of stored mappings."""
        raise NotImplementedError


class InMemoryStorage(URLStorage):
    """
    Hash map backed storage. O(1) average time for save, get, and
    exists, since a Python dict is a hash table under the hood. Useful
    for tests and local development where a database is overkill.
    """

    def __init__(self):
        self._store: dict[str, str] = {}
        self._lock = threading.Lock()

    def save(self, short_code: str, long_url: str) -> None:
        with self._lock:
            self._store[short_code] = long_url

    def get(self, short_code: str) -> Optional[str]:
        return self._store.get(short_code)

    def exists(self, short_code: str) -> bool:
        return short_code in self._store

    def count(self) -> int:
        return len(self._store)


class SQLiteStorage(URLStorage):
    """
    SQLite backed storage. Same interface as InMemoryStorage, so the
    service layer is unaffected by the swap. In production this class
    could be replaced with a Postgres or DynamoDB implementation
    without touching any other file.
    """

    def __init__(self, db_path: str = "shortener.db"):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS urls (
                    short_code TEXT PRIMARY KEY,
                    long_url TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def save(self, short_code: str, long_url: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO urls (short_code, long_url) VALUES (?, ?)",
                (short_code, long_url),
            )
            conn.commit()

    def get(self, short_code: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT long_url FROM urls WHERE short_code = ?", (short_code,)
            ).fetchone()
            return row[0] if row else None

    def exists(self, short_code: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM urls WHERE short_code = ?", (short_code,)
            ).fetchone()
            return row is not None

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM urls").fetchone()
            return row[0]
