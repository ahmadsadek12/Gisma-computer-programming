"""Repository metadata model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Repository:
    """GitHub repository summary for listing and analysis navigation."""

    name: str
    owner: str
    description: str
    visibility: str
    language: Optional[str]
    stars: int
    forks: int
    updated_at: str
    html_url: str

    @staticmethod
    def from_api(item: dict[str, Any]) -> "Repository":
        owner = item.get("owner") or {}
        login = owner.get("login") or ""
        vis = item.get("visibility") or "unknown"
        return Repository(
            name=item.get("name") or "",
            owner=login,
            description=(item.get("description") or "") or "",
            visibility=vis,
            language=item.get("language"),
            stars=int(item.get("stargazers_count") or 0),
            forks=int(item.get("forks_count") or 0),
            updated_at=item.get("updated_at") or "",
            html_url=item.get("html_url") or "",
        )
