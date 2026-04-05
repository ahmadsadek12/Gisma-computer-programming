"""
Heuristic merge-conflict risk: same file touched by different authors in recent commits.
Does not run git merge.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from services.github_service import GitHubService


@dataclass
class ConflictRisk:
    """A single potential conflict-risk finding."""

    file_path: str
    contributor_a: str
    contributor_b: str
    commit_hash_a: str
    commit_hash_b: str
    date_a: str
    date_b: str
    risk_level: str  # High, Medium, Low
    explanation: str
    recommendation: str


class ConflictDetector:
    """
    Loads per-commit file lists for recent SHAs and flags same-file, different-author
    pairs with time-based risk tiers.
    """

    def __init__(self, github: GitHubService) -> None:
        self._gh = github

    def detect(
        self,
        owner: str,
        repo_name: str,
        shas: list[str],
    ) -> list[ConflictRisk]:
        """
        For each SHA (newest first), fetch commit detail and collect file paths.
        For each file, compare latest touch per distinct author; pairwise delta in days.
        """
        # file -> author -> (latest_datetime, sha, iso_date_str)
        file_author_latest: dict[
            str, dict[str, tuple[datetime, str, str]]
        ] = {}

        for sha in shas:
            try:
                detail = self._gh.get_commit_detail(owner, repo_name, sha)
            except Exception:
                continue
            commit = detail.get("commit") or {}
            author = commit.get("author") or {}
            date_str = author.get("date") or ""
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                dt = datetime.now(timezone.utc)
            gh_author = detail.get("author") or {}
            login = gh_author.get("login")
            if not login:
                login = (author.get("name") or "unknown").strip()

            files = detail.get("files") or []
            paths = {f.get("filename") for f in files if f.get("filename")}
            for path in paths:
                if path not in file_author_latest:
                    file_author_latest[path] = {}
                prev = file_author_latest[path].get(login)
                if prev is None or dt > prev[0]:
                    file_author_latest[path][login] = (dt, sha, date_str)

        risks: list[ConflictRisk] = []
        for path, by_auth in file_author_latest.items():
            authors = list(by_auth.keys())
            if len(authors) < 2:
                continue
            for i, a1 in enumerate(authors):
                for a2 in authors[i + 1 :]:
                    if a1 == a2:
                        continue
                    dt1, sha1, dstr1 = by_auth[a1]
                    dt2, sha2, dstr2 = by_auth[a2]
                    delta_days = abs((dt1 - dt2).total_seconds()) / 86400.0

                    if delta_days <= 2.0:
                        level = "High"
                        expl = (
                            f"Authors '{a1}' and '{a2}' modified this file within "
                            f"about {delta_days:.1f} days — high overlap risk."
                        )
                        rec = (
                            "Manual review recommended before integrating both lines "
                            "of work; consider coordinating or serializing changes."
                        )
                    elif delta_days <= 7.0:
                        level = "Medium"
                        expl = (
                            f"Different authors touched this file within "
                            f"{delta_days:.1f} days — possible integration friction."
                        )
                        rec = (
                            "Prefer manual review or merging in order of dependency; "
                            "latest commit does not automatically win in Git."
                        )
                    elif delta_days <= 30.0:
                        level = "Low"
                        expl = (
                            f"Same file edited by different authors "
                            f"{delta_days:.1f} days apart — lower urgency but still "
                            f"worth awareness for parallel work."
                        )
                        rec = (
                            "Schedule a quick sync if both contributors continue "
                            f"on this file; otherwise monitor."
                        )
                    else:
                        continue

                    # Order hashes consistently for storage
                    if dt1 >= dt2:
                        ca, cb = a1, a2
                        ha, hb = sha1, sha2
                        da, db = dstr1, dstr2
                    else:
                        ca, cb = a2, a1
                        ha, hb = sha2, sha1
                        da, db = dstr2, dstr1

                    risks.append(
                        ConflictRisk(
                            file_path=path,
                            contributor_a=ca,
                            contributor_b=cb,
                            commit_hash_a=ha,
                            commit_hash_b=hb,
                            date_a=da,
                            date_b=db,
                            risk_level=level,
                            explanation=expl,
                            recommendation=rec,
                        )
                    )

        risks.sort(
            key=lambda r: (
                {"High": 0, "Medium": 1, "Low": 2}.get(r.risk_level, 3),
                r.file_path,
            )
        )
        return risks
