"""Filter commit records by regex on commit messages."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable, Optional, TypeVar

if TYPE_CHECKING:
    from models.commit_record import CommitRecord

T = TypeVar("T")


class RegexFilter:
    """
    Applies a user-supplied regex pattern to filter items that expose a message string.
    """

    @classmethod
    def filter_commits(
        cls,
        commits: list["CommitRecord"],
        pattern: str,
    ) -> tuple[list["CommitRecord"], Optional[str]]:
        """
        Filter commits by regex on message.
        Returns (filtered, error_message); error_message is set on invalid regex.
        """
        return cls.filter_by_message(commits, lambda c: c.message, pattern)

    @staticmethod
    def filter_by_message(
        items: list[T],
        get_message: Callable[[T], str],
        pattern: str,
    ) -> tuple[list[T], Optional[str]]:
        """
        Return (filtered_items, error_message).
        If pattern is empty, returns all items and no error.
        On invalid regex, returns ([], error string).
        """
        p = pattern.strip()
        if not p:
            return list(items), None
        try:
            cre = re.compile(p, re.IGNORECASE | re.DOTALL)
        except re.error as e:
            return [], f"Invalid regex: {e}"

        out: list[T] = []
        for it in items:
            msg = get_message(it) or ""
            if cre.search(msg):
                out.append(it)
        return out, None
