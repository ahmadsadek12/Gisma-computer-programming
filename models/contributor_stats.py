"""Per-contributor analytics derived from commit history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ContributorStats:
    github_username: str
    display_name: Optional[str]
    commit_count: int
    first_commit_date: str
    last_commit_date: str
    latest_commit_hash: str
    latest_commit_message: str
