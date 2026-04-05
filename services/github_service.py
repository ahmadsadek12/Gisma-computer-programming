"""GitHub REST API client using requests."""

from __future__ import annotations

from typing import Any, Optional

import requests

from models.repository import Repository


class GitHubAPIError(Exception):
    """Raised when the GitHub API returns an error or the request fails."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubService:
    """GitHub REST API v3 client with token auth and error handling."""

    BASE = "https://api.github.com"

    def __init__(self, token: str) -> None:
        self._token = token.strip()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"token {self._token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "GitHub-Repository-Analyzer-Desktop",
            }
        )

    def _check_rate_limit(self, response: requests.Response) -> None:
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining is not None and remaining == "0":
            reset = response.headers.get("X-RateLimit-Reset", "?")
            raise GitHubAPIError(
                f"GitHub API rate limit exceeded. Reset epoch: {reset}.",
                status_code=response.status_code,
            )

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Any:
        try:
            r = self._session.request(method, url, params=params, timeout=timeout)
        except requests.RequestException as e:
            raise GitHubAPIError(f"Network error: {e}") from e

        self._check_rate_limit(r)

        if r.status_code == 401:
            raise GitHubAPIError(
                "Invalid or expired token (401). Check your Personal Access Token.",
                status_code=401,
            )
        if r.status_code == 403:
            raise GitHubAPIError(
                "Access forbidden (403). Token may lack required scopes or repo is inaccessible.",
                status_code=403,
            )
        if r.status_code == 404:
            raise GitHubAPIError("Resource not found (404).", status_code=404)
        if r.status_code == 429:
            raise GitHubAPIError(
                "Too many requests (429). Try again later.", status_code=429
            )
        if r.status_code >= 500:
            raise GitHubAPIError(
                f"GitHub server error ({r.status_code}).", status_code=r.status_code
            )
        if r.status_code >= 400:
            try:
                err = r.json().get("message", r.text)
            except ValueError:
                err = r.text
            raise GitHubAPIError(
                f"Request failed ({r.status_code}): {err}",
                status_code=r.status_code,
            )

        if r.status_code == 204:
            return None
        try:
            return r.json()
        except ValueError as e:
            raise GitHubAPIError("Invalid JSON in API response.") from e

    def verify_token(self) -> dict[str, Any]:
        """GET /user — returns authenticated user payload."""
        data = self._request("GET", f"{self.BASE}/user")
        return data if isinstance(data, dict) else {}

    def get_user_profile(self, login: str) -> dict[str, Any]:
        """
        GET /users/{login} — public profile (name, bio, etc.).
        Used to enrich contributor display names when available.
        """
        login = login.strip()
        if not login:
            return {}
        try:
            data = self._request("GET", f"{self.BASE}/users/{login}")
            return data if isinstance(data, dict) else {}
        except GitHubAPIError as e:
            if e.status_code == 404:
                return {}
            raise

    def list_repositories(self, max_repos: int = 100) -> list[Repository]:
        """GET /user/repos (paginated)."""
        out: list[Repository] = []
        page = 1
        per_page = min(100, max_repos)
        while len(out) < max_repos:
            data = self._request(
                "GET",
                f"{self.BASE}/user/repos",
                params={
                    "per_page": per_page,
                    "page": page,
                    "sort": "updated",
                    "direction": "desc",
                },
            )
            if not isinstance(data, list) or not data:
                break
            for item in data:
                out.append(Repository.from_api(item))
                if len(out) >= max_repos:
                    break
            if len(data) < per_page:
                break
            page += 1
        return out

    def get_repo_commits(
        self,
        owner: str,
        repo: str,
        per_page: int = 100,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        data = self._request(
            "GET",
            f"{self.BASE}/repos/{owner}/{repo}/commits",
            params={"per_page": per_page, "page": page},
        )
        return data if isinstance(data, list) else []

    def get_commit_detail(
        self, owner: str, repo: str, sha: str
    ) -> dict[str, Any]:
        data = self._request(
            "GET",
            f"{self.BASE}/repos/{owner}/{repo}/commits/{sha}",
        )
        return data if isinstance(data, dict) else {}

    def get_contributors(
        self, owner: str, repo: str, per_page: int = 100
    ) -> list[dict[str, Any]]:
        data = self._request(
            "GET",
            f"{self.BASE}/repos/{owner}/{repo}/contributors",
            params={"per_page": per_page, "page": 1},
        )
        return data if isinstance(data, list) else []

    def get_repository(self, owner: str, repo: str) -> Repository:
        data = self._request("GET", f"{self.BASE}/repos/{owner}/{repo}")
        if not isinstance(data, dict):
            raise GitHubAPIError("Unexpected repository response.")
        return Repository.from_api(data)
