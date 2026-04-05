"""Single commit record for tables and analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class CommitRecord:
    sha: str
    short_sha: str
    author_login: str
    message: str
    committed_at: str  # ISO 8601 from API

    @staticmethod
    def from_api(commit: dict[str, Any]) -> "CommitRecord":
        sha = commit.get("sha") or ""
        short_sha = sha[:7] if len(sha) >= 7 else sha
        c = commit.get("commit") or {}
        author = c.get("author") or {}
        committer = c.get("committer") or {}
        # Prefer GitHub login from top-level author if present
        gh_author = commit.get("author") or {}
        login = gh_author.get("login")
        if not login:
            login = (author.get("name") or committer.get("name") or "unknown").strip()
        msg = (c.get("message") or "").split("\n")[0]
        date = author.get("date") or committer.get("date") or ""
        return CommitRecord(
            sha=sha,
            short_sha=short_sha,
            author_login=login,
            message=msg,
            committed_at=date,
        )

    def committed_datetime(self) -> Optional[datetime]:
        if not self.committed_at:
            return None
        try:
            return datetime.fromisoformat(self.committed_at.replace("Z", "+00:00"))
        except ValueError:
            return None
