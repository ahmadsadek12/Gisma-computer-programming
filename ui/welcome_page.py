"""Landing screen with login and sign up."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.app import App


class WelcomePage(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: App, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)
        self._app = app

        inner = ttk.Frame(self, padding=24)
        inner.pack(expand=True)

        ttk.Label(inner, text="GitHub Repository Analyzer", style="Title.TLabel").pack(
            pady=(0, 8)
        )
        ttk.Label(
            inner,
            text=(
                "Analyze commit history, contributors, and activity for your GitHub "
                "repositories — with regex filtering, charts, exports, and "
                "conflict-risk hints."
            ),
            wraplength=520,
            justify=tk.CENTER,
        ).pack(pady=(0, 24))

        if app.current_user:
            logged = ttk.LabelFrame(inner, text="You are signed in", padding=8)
            logged.pack(pady=(0, 16), fill=tk.X)
            ttk.Label(
                logged,
                text=f"Logged in as {app.current_user.username} ({app.current_user.email})",
            ).pack(anchor=tk.CENTER, pady=(0, 8))
            ttk.Button(
                logged,
                text="Go to Dashboard",
                command=lambda: app.show_page("dashboard"),
                width=22,
            ).pack()
        else:
            btnf = ttk.Frame(inner)
            btnf.pack()
            ttk.Button(btnf, text="Log In", command=self._login, width=18).pack(
                side=tk.LEFT, padx=6
            )
            ttk.Button(btnf, text="Sign Up", command=self._signup, width=18).pack(
                side=tk.LEFT, padx=6
            )

    def _login(self) -> None:
        self._app.show_page("login")

    def _signup(self) -> None:
        self._app.show_page("signup")
