"""
Fetches commit history and builds contributor analytics, chart datasets, and message categories.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from models.commit_record import CommitRecord
from models.contributor_stats import ContributorStats
from services.github_service import GitHubAPIError, GitHubService


# Fetch limits (see README)
DEFAULT_MAX_COMMITS = 400
FILE_DETAIL_COMMITS = 90


@dataclass
class AnalysisResult:
    """Complete outcome of analyzing a single repository."""

    owner: str
    repo_name: str
    repo_description: Optional[str] = None
    commits: list[CommitRecord] = field(default_factory=list)
    contributor_stats: list[ContributorStats] = field(default_factory=list)
    total_commits: int = 0
    total_contributors: int = 0
    latest_commit_date: str = ""
    latest_commit_hash: str = ""
    latest_commit_message: str = ""
    most_active_contributor: str = ""
    commits_per_contributor: dict[str, int] = field(default_factory=dict)
    commits_per_day: list[tuple[str, int]] = field(default_factory=list)
    message_categories: dict[str, int] = field(default_factory=dict)
    # For conflict detection: SHAs to request file lists for (most recent first)
    shas_for_file_inspection: list[str] = field(default_factory=list)
    # Optional: length of GET /repos/{owner}/{repo}/contributors (API supplement)
    github_contributors_endpoint_count: Optional[int] = None
    error_message: Optional[str] = None


def _enrich_display_names(
    github: GitHubService, stats: list[ContributorStats], max_profiles: int = 15
) -> None:
    """Fill display_name from GET /users/{login} when possible (capped API calls)."""
    api_calls = 0
    for s in stats:
        if api_calls >= max_profiles:
            break
        login = (s.github_username or "").strip()
        if not login or login.lower() == "unknown" or " " in login:
            continue
        try:
            prof = github.get_user_profile(login)
            name = (prof.get("name") or "").strip()
            if name:
                s.display_name = name
        except GitHubAPIError:
            pass
        api_calls += 1


_CATEGORY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)\bfix\b"), "fix"),
    (re.compile(r"(?i)\bfeat(ure)?\b"), "feat"),
    (re.compile(r"(?i)\bmerge\b"), "merge"),
    (re.compile(r"(?i)\bdocs?\b"), "docs"),
    (re.compile(r"(?i)\brefactor\b"), "refactor"),
    (re.compile(r"(?i)\btest\b"), "test"),
]


def _categorize_message(msg: str) -> str:
    first = (msg or "").split("\n")[0]
    for pat, name in _CATEGORY_RULES:
        if pat.search(first):
            return name
    return "other"


class RepositoryAnalyzer:
    """Analyzes GitHub commit history for a repository."""

    def __init__(self, github: GitHubService) -> None:
        self._gh = github

    def analyze(
        self,
        owner: str,
        repo_name: str,
        max_commits: int = DEFAULT_MAX_COMMITS,
        file_detail_limit: int = FILE_DETAIL_COMMITS,
    ) -> AnalysisResult:
        result = AnalysisResult(owner=owner, repo_name=repo_name)
        try:
            repo_meta = self._gh.get_repository(owner, repo_name)
            result.repo_description = repo_meta.description or ""
        except GitHubAPIError as e:
            result.error_message = str(e)
            return result

        try:
            api_contribs = self._gh.get_contributors(owner, repo_name)
            result.github_contributors_endpoint_count = len(api_contribs)
        except GitHubAPIError:
            pass

        raw_commits: list[dict[str, Any]] = []
        page = 1
        per_page = min(100, max_commits)

        try:
            while len(raw_commits) < max_commits:
                batch = self._gh.get_repo_commits(
                    owner, repo_name, per_page=per_page, page=page
                )
                if not batch:
                    break
                raw_commits.extend(batch)
                if len(batch) < per_page:
                    break
                page += 1
                if len(raw_commits) >= max_commits:
                    break
        except Exception as e:
            result.error_message = str(e)
            return result

        raw_commits = raw_commits[:max_commits]
        commits: list[CommitRecord] = []
        for rc in raw_commits:
            try:
                commits.append(CommitRecord.from_api(rc))
            except Exception:
                continue

        result.commits = commits
        result.total_commits = len(commits)

        if not commits:
            result.error_message = (
                "No commits found (empty repository or no access)."
            )
            return result

        # Latest = first in API order (typically chronological desc)
        latest = commits[0]
        result.latest_commit_date = latest.committed_at
        result.latest_commit_hash = latest.sha
        result.latest_commit_message = latest.message

        # Contributor aggregation
        by_author: dict[str, list[CommitRecord]] = defaultdict(list)
        for c in commits:
            by_author[c.author_login].append(c)

        def commit_time_key(cr: CommitRecord) -> datetime:
            dt = cr.committed_datetime()
            if dt:
                return dt
            return datetime.min.replace(tzinfo=timezone.utc)

        stats_list: list[ContributorStats] = []
        commits_per_contributor: dict[str, int] = {}

        for login, clist in sorted(by_author.items(), key=lambda x: (-len(x[1]), x[0])):
            clist_sorted = sorted(clist, key=commit_time_key)
            first = clist_sorted[0]
            last = clist_sorted[-1]
            latest_c = clist_sorted[-1]
            commits_per_contributor[login] = len(clist)
            disp: Optional[str] = None
            if login and not login.lower().startswith("unknown"):
                disp = login
            stats_list.append(
                ContributorStats(
                    github_username=login,
                    display_name=disp,
                    commit_count=len(clist),
                    first_commit_date=first.committed_at,
                    last_commit_date=last.committed_at,
                    latest_commit_hash=latest_c.sha,
                    latest_commit_message=latest_c.message,
                )
            )

        result.contributor_stats = sorted(
            stats_list, key=lambda s: -s.commit_count
        )
        _enrich_display_names(self._gh, result.contributor_stats)
        result.total_contributors = len(result.contributor_stats)
        result.commits_per_contributor = commits_per_contributor
        if result.contributor_stats:
            result.most_active_contributor = result.contributor_stats[0].github_username

        # Commits per day (UTC date)
        day_counts: dict[str, int] = defaultdict(int)
        for c in commits:
            dt = c.committed_datetime()
            if dt:
                dkey = dt.astimezone(timezone.utc).date().isoformat()
                day_counts[dkey] += 1
            elif c.committed_at:
                day_counts[c.committed_at[:10]] += 1

        result.commits_per_day = sorted(day_counts.items())

        # Message categories
        cats: dict[str, int] = defaultdict(int)
        for c in commits:
            cats[_categorize_message(c.message)] += 1
        result.message_categories = dict(cats)

        # SHAs for conflict file inspection (most recent first)
        result.shas_for_file_inspection = [c.sha for c in commits[:file_detail_limit]]

        return result
