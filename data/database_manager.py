"""
SQLite persistence for users, GitHub connections, favorites, history, and conflict logs.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

from utils.security import verify_password


class DatabaseManager:
    """Manages SQLite connection and schema for the application."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """
        Default path: ``<project>/database/app.db``.

        Override with ``db_path`` or environment variable ``DATABASE_PATH``.
        """
        root = Path(__file__).resolve().parents[1]
        if db_path is not None:
            self._db_path = db_path
        else:
            env = os.environ.get("DATABASE_PATH", "").strip()
            self._db_path = Path(env) if env else (root / "database" / "app.db")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def db_path(self) -> Path:
        """Resolved path to the SQLite database file."""
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        """Create tables if they do not exist."""
        try:
            with self._connect() as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS github_connections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        github_username TEXT NOT NULL,
                        token TEXT NOT NULL,
                        connected_at TEXT NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    );

                    CREATE TABLE IF NOT EXISTS favorite_repositories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        repo_name TEXT NOT NULL,
                        repo_owner TEXT NOT NULL,
                        repo_url TEXT,
                        saved_at TEXT NOT NULL,
                        UNIQUE(user_id, repo_name, repo_owner),
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    );

                    CREATE TABLE IF NOT EXISTS analysis_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        repo_name TEXT NOT NULL,
                        repo_owner TEXT NOT NULL,
                        total_commits INTEGER,
                        total_contributors INTEGER,
                        last_analyzed_at TEXT NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    );

                    CREATE TABLE IF NOT EXISTS conflict_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        repo_name TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        author_1 TEXT NOT NULL,
                        author_2 TEXT NOT NULL,
                        commit_hash_1 TEXT NOT NULL,
                        commit_hash_2 TEXT NOT NULL,
                        risk_level TEXT NOT NULL,
                        detected_at TEXT NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    );
                    """
                )
                conn.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Database initialization failed: {e}") from e

    def create_user(
        self, username: str, email: str, password_hash: str, created_at: str
    ) -> int:
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO users (username, email, password_hash, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, email, password_hash, created_at),
                )
                conn.commit()
                return int(cur.lastrowid)
        except sqlite3.IntegrityError as e:
            raise ValueError("Username or email already registered.") from e
        except sqlite3.Error as e:
            raise RuntimeError(f"Could not create user: {e}") from e

    def get_user_by_username(self, username: str) -> Optional[dict[str, Any]]:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM users WHERE username = ?", (username,)
                ).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}") from e

    def get_user_by_email(self, email: str) -> Optional[dict[str, Any]]:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM users WHERE email = ?", (email,)
                ).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}") from e

    def get_user_by_id(self, user_id: int) -> Optional[dict[str, Any]]:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM users WHERE id = ?", (user_id,)
                ).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}") from e

    def authenticate(self, username_or_email: str, password: str) -> Optional[dict[str, Any]]:
        """Return user row if credentials match, else None."""
        raw = username_or_email.strip()
        user = self.get_user_by_username(raw)
        if not user and "@" in raw:
            user = self.get_user_by_email(raw.lower())
        if not user:
            return None
        if not verify_password(password, user["password_hash"]):
            return None
        return user

    def save_github_connection(
        self,
        user_id: int,
        github_username: str,
        token: str,
        connected_at: str,
    ) -> None:
        try:
            with self._connect() as conn:
                existing = conn.execute(
                    "SELECT id FROM github_connections WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                if existing:
                    conn.execute(
                        """
                        UPDATE github_connections
                        SET github_username = ?, token = ?, connected_at = ?
                        WHERE user_id = ?
                        """,
                        (github_username, token, connected_at, user_id),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO github_connections
                        (user_id, github_username, token, connected_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (user_id, github_username, token, connected_at),
                    )
                conn.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Could not save GitHub connection: {e}") from e

    def get_github_connection(self, user_id: int) -> Optional[dict[str, Any]]:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM github_connections WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}") from e

    def add_favorite(
        self,
        user_id: int,
        repo_name: str,
        repo_owner: str,
        repo_url: Optional[str],
        saved_at: str,
    ) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO favorite_repositories
                    (user_id, repo_name, repo_owner, repo_url, saved_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, repo_name, repo_owner, repo_url, saved_at),
                )
                conn.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Could not add favorite: {e}") from e

    def remove_favorite(self, user_id: int, repo_name: str, repo_owner: str) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    DELETE FROM favorite_repositories
                    WHERE user_id = ? AND repo_name = ? AND repo_owner = ?
                    """,
                    (user_id, repo_name, repo_owner),
                )
                conn.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Could not remove favorite: {e}") from e

    def is_favorite(self, user_id: int, repo_name: str, repo_owner: str) -> bool:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT 1 FROM favorite_repositories
                    WHERE user_id = ? AND repo_name = ? AND repo_owner = ?
                    """,
                    (user_id, repo_name, repo_owner),
                ).fetchone()
                return row is not None
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}") from e

    def list_favorites(self, user_id: int) -> list[dict[str, Any]]:
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM favorite_repositories
                    WHERE user_id = ? ORDER BY saved_at DESC
                    """,
                    (user_id,),
                ).fetchall()
                return [dict(r) for r in rows]
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}") from e

    def add_analysis_history(
        self,
        user_id: int,
        repo_name: str,
        repo_owner: str,
        total_commits: Optional[int],
        total_contributors: Optional[int],
        last_analyzed_at: str,
    ) -> int:
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO analysis_history
                    (user_id, repo_name, repo_owner, total_commits,
                     total_contributors, last_analyzed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        repo_name,
                        repo_owner,
                        total_commits,
                        total_contributors,
                        last_analyzed_at,
                    ),
                )
                conn.commit()
                return int(cur.lastrowid)
        except sqlite3.Error as e:
            raise RuntimeError(f"Could not save analysis history: {e}") from e

    def list_analysis_history(self, user_id: int) -> list[dict[str, Any]]:
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM analysis_history
                    WHERE user_id = ? ORDER BY last_analyzed_at DESC
                    """,
                    (user_id,),
                ).fetchall()
                return [dict(r) for r in rows]
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}") from e

    def add_conflict_log(
        self,
        user_id: int,
        repo_name: str,
        file_path: str,
        author_1: str,
        author_2: str,
        commit_hash_1: str,
        commit_hash_2: str,
        risk_level: str,
        detected_at: str,
    ) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO conflict_logs
                    (user_id, repo_name, file_path, author_1, author_2,
                     commit_hash_1, commit_hash_2, risk_level, detected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        repo_name,
                        file_path,
                        author_1,
                        author_2,
                        commit_hash_1,
                        commit_hash_2,
                        risk_level,
                        detected_at,
                    ),
                )
                conn.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Could not save conflict log: {e}") from e

    def list_conflict_logs(
        self, user_id: int, repo_name: Optional[str] = None
    ) -> list[dict[str, Any]]:
        try:
            with self._connect() as conn:
                if repo_name:
                    rows = conn.execute(
                        """
                        SELECT * FROM conflict_logs
                        WHERE user_id = ? AND repo_name = ?
                        ORDER BY detected_at DESC
                        """,
                        (user_id, repo_name),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT * FROM conflict_logs
                        WHERE user_id = ?
                        ORDER BY detected_at DESC
                        """,
                        (user_id,),
                    ).fetchall()
                return [dict(r) for r in rows]
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}") from e

    def count_favorites(self, user_id: int) -> int:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) AS c FROM favorite_repositories WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                return int(row["c"]) if row else 0
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}") from e

    def count_analyses(self, user_id: int) -> int:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) AS c FROM analysis_history WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                return int(row["c"]) if row else 0
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}") from e
