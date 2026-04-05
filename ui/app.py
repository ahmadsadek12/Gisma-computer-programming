"""
Main Tkinter application shell: navigation and shared state.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Optional

from data.database_manager import DatabaseManager
from models.user import User
from services.auth_service import AuthService
from services.github_service import GitHubService
from services.report_exporter import ReportExporter


class App(tk.Tk):
    """
    Root window. Holds database access, current user, navigation, and analysis cache.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        super().__init__()
        self.title("GitHub Repository Analyzer")
        self.minsize(960, 640)
        self.geometry("1100x720")

        self._db = db_manager
        self._auth = AuthService(db_manager)
        self.current_user: Optional[User] = None

        self._analysis: Any = None
        self._conflict_risks: list[Any] = []
        self._selected_repo: Any = None
        self._repos_cache: list[Any] = []

        root = self._project_root()
        self.exports_path = root / "exports"
        self.exports_path.mkdir(parents=True, exist_ok=True)
        self.exporter = ReportExporter(self.exports_path)

        self._container = ttk.Frame(self, padding=12)
        self._container.pack(fill=tk.BOTH, expand=True)

        self._style = ttk.Style()
        if "vista" in self._style.theme_names():
            self._style.theme_use("vista")
        self._style.configure("TButton", padding=6)
        self._style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        self._style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))

        from ui.welcome_page import WelcomePage

        self._current_page: Optional[ttk.Frame] = None
        self.show_page("welcome")

    @staticmethod
    def _project_root() -> Any:
        from pathlib import Path

        return Path(__file__).resolve().parents[1]

    @property
    def db(self) -> DatabaseManager:
        return self._db

    @property
    def auth(self) -> AuthService:
        return self._auth

    def set_user(self, user: Optional[User]) -> None:
        self.current_user = user

    def set_analysis_context(
        self,
        analysis: Optional[Any] = None,
        repo_meta: Any = None,
        conflicts: Optional[list[Any]] = None,
    ) -> None:
        self._analysis = analysis
        self._selected_repo = repo_meta
        if analysis is None:
            self._conflict_risks = []
        elif conflicts is not None:
            self._conflict_risks = conflicts

    @property
    def current_analysis(self) -> Any:
        return self._analysis

    @property
    def selected_repo(self) -> Any:
        return self._selected_repo

    @property
    def conflict_risks(self) -> list[Any]:
        return self._conflict_risks

    def set_repos_cache(self, repos: list[Any]) -> None:
        self._repos_cache = repos

    @property
    def repos_cache(self) -> list[Any]:
        return self._repos_cache

    def get_github_service(self) -> GitHubService:
        if not self.current_user:
            raise RuntimeError("Not logged in.")
        row = self._db.get_github_connection(self.current_user.id)
        if not row:
            raise RuntimeError("GitHub is not connected.")
        return GitHubService(row["token"])

    def set_busy_cursor(self, busy: bool) -> None:
        """Wait cursor on the root window (safe when background work outlives a page)."""
        try:
            self.config(cursor="watch" if busy else "")
        except tk.TclError:
            pass

    def show_page(self, name: str, **kwargs: Any) -> None:
        for w in self._container.winfo_children():
            w.destroy()

        factory: dict[str, Callable[..., ttk.Frame]] = {
            "welcome": _lazy("ui.welcome_page", "WelcomePage"),
            "signup": _lazy("ui.signup_page", "SignUpPage"),
            "login": _lazy("ui.login_page", "LoginPage"),
            "dashboard": _lazy("ui.dashboard_page", "DashboardPage"),
            "connect_github": _lazy("ui.connect_github_page", "ConnectGitHubPage"),
            "repo_list": _lazy("ui.repo_list_page", "RepoListPage"),
            "analysis": _lazy("ui.repo_analysis_page", "RepoAnalysisPage"),
            "conflict": _lazy("ui.conflict_page", "ConflictPage"),
            "history": _lazy("ui.history_page", "HistoryPage"),
        }
        cls = factory.get(name)
        if not cls:
            raise ValueError(f"Unknown page: {name}")
        self._current_page = cls(self._container, self, **kwargs)
        self._current_page.pack(fill=tk.BOTH, expand=True)


def _lazy(module: str, class_name: str) -> Callable[..., ttk.Frame]:
    def _load(parent: tk.Widget, app: App, **kwargs: Any) -> ttk.Frame:
        mod = __import__(module, fromlist=[class_name])
        cls = getattr(mod, class_name)
        return cls(parent, app, **kwargs)

    return _load
