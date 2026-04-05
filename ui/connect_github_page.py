"""Save and verify GitHub PAT + username."""

from __future__ import annotations

from datetime import datetime, timezone

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.app import App


class ConnectGitHubPage(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: App, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)
        self._app = app

        if not app.current_user:
            app.show_page("welcome")
            return

        ttk.Label(self, text="Connect GitHub", style="Header.TLabel").pack(
            anchor=tk.W, pady=(0, 8)
        )
        ttk.Label(
            self,
            text=(
                "Enter your GitHub username and a Personal Access Token (classic) "
                "with at least repo read scope for private repositories you own."
            ),
            wraplength=640,
        ).pack(anchor=tk.W, pady=(0, 12))

        self._gh_user = tk.StringVar()
        self._token = tk.StringVar()

        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="GitHub username", width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self._gh_user, width=48).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

        row2 = ttk.Frame(self)
        row2.pack(fill=tk.X, pady=4)
        ttk.Label(row2, text="Personal Access Token", width=18).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self._token, width=48, show="*").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

        self._msg = tk.StringVar(value="")
        ttk.Label(
            self,
            textvariable=self._msg,
            foreground="#0a5",
            wraplength=640,
        ).pack(anchor=tk.W, pady=8)

        bf = ttk.Frame(self)
        bf.pack(fill=tk.X, pady=12)
        ttk.Button(bf, text="Back", command=self._back).pack(side=tk.LEFT)
        ttk.Button(bf, text="Test connection", command=self._test).pack(
            side=tk.LEFT, padx=8
        )
        ttk.Button(bf, text="Save connection", command=self._save).pack(
            side=tk.RIGHT
        )

        conn = app.db.get_github_connection(app.current_user.id)
        if conn:
            self._gh_user.set(conn["github_username"])
            self._token.set(conn["token"])

    def _back(self) -> None:
        self._app.show_page("dashboard")

    def _test(self) -> None:
        from services.github_service import GitHubAPIError, GitHubService

        try:
            svc = GitHubService(self._token.get())
            user = svc.verify_token()
            login = user.get("login", "?")
            self._msg.set(f"OK — authenticated as {login}")
        except GitHubAPIError as e:
            self._msg.set("")
            messagebox.showerror("GitHub", str(e))
        except Exception as e:
            self._msg.set("")
            messagebox.showerror("GitHub", str(e))

    def _save(self) -> None:
        from services.github_service import GitHubAPIError, GitHubService

        u = self._app.current_user
        if not u:
            return
        gh_name = self._gh_user.get().strip()
        tok = self._token.get().strip()
        if not gh_name or not tok:
            messagebox.showwarning("GitHub", "Username and token are required.")
            return
        try:
            svc = GitHubService(tok)
            api_user = svc.verify_token()
            api_login = (api_user.get("login") or "").lower()
            if api_login and gh_name.lower() != api_login:
                if not messagebox.askyesno(
                    "Confirm",
                    f"Token belongs to '{api_login}' but you entered '{gh_name}'. Save anyway?",
                ):
                    return
            now = datetime.now(timezone.utc).isoformat()
            self._app.db.save_github_connection(u.id, gh_name, tok, now)
            self._msg.set("Connection saved.")
            messagebox.showinfo("GitHub", "Connection saved.")
        except GitHubAPIError as e:
            messagebox.showerror("GitHub", str(e))
        except Exception as e:
            messagebox.showerror("GitHub", str(e))
