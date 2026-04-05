"""Post-login hub."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.app import App


class DashboardPage(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: App, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)
        self._app = app

        if not app.current_user:
            app.show_page("welcome")
            return

        u = app.current_user
        nav = ttk.Frame(self)
        nav.pack(fill=tk.X, anchor=tk.W, pady=(0, 8))
        ttk.Button(nav, text="Back", command=self._back).pack(side=tk.LEFT)

        ttk.Label(self, text=f"Welcome, {u.username}", style="Header.TLabel").pack(
            anchor=tk.W, pady=(0, 8)
        )
        ttk.Label(self, text=f"Email: {u.email}").pack(anchor=tk.W)

        gh = app.db.get_github_connection(u.id)
        status = (
            f"Connected as {gh['github_username']}" if gh else "Not connected"
        )
        ttk.Label(self, text=f"GitHub: {status}", wraplength=600).pack(
            anchor=tk.W, pady=(8, 4)
        )

        try:
            fav_n = app.db.count_favorites(u.id)
            ana_n = app.db.count_analyses(u.id)
        except Exception:
            fav_n, ana_n = 0, 0
        ttk.Label(self, text=f"Favorites: {fav_n}  |  Analyses logged: {ana_n}").pack(
            anchor=tk.W, pady=(4, 16)
        )

        grid = ttk.Frame(self)
        grid.pack(fill=tk.X, pady=8)

        def btn(text: str, cmd: object) -> None:
            ttk.Button(grid, text=text, command=cmd, width=28).pack(
                fill=tk.X, pady=4
            )

        btn("Connect GitHub", lambda: app.show_page("connect_github"))
        btn("View Repositories", lambda: app.show_page("repo_list"))
        btn("View Favorites", lambda: app.show_page("history", initial_tab=0))
        btn("View History", lambda: app.show_page("history", initial_tab=1))
        btn("Log out", self._logout)

    def _back(self) -> None:
        self._app.show_page("welcome")

    def _logout(self) -> None:
        self._app.set_user(None)
        self._app.set_analysis_context(None)
        self._app.show_page("welcome")
