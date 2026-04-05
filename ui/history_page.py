"""Favorites and past analysis history with reopen."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from threading import Thread
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ui.app import App


class HistoryPage(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: App, **kwargs: object) -> None:
        initial_tab = int(kwargs.pop("initial_tab", 0))
        super().__init__(parent, **kwargs)
        self._app = app
        if not app.current_user:
            app.show_page("welcome")
            return

        ttk.Label(self, text="Favorites & analysis history", style="Header.TLabel").pack(
            anchor=tk.W, pady=(0, 8)
        )

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)

        self._fav_frame = ttk.Frame(nb, padding=6)
        self._hist_frame = ttk.Frame(nb, padding=6)
        nb.add(self._fav_frame, text="Favorites")
        nb.add(self._hist_frame, text="Analysis history")
        if initial_tab == 1:
            nb.select(self._hist_frame)

        # Favorites
        fcols = ("owner", "name", "url", "saved")
        self._fav_tree = ttk.Treeview(
            self._fav_frame, columns=fcols, show="headings", height=12
        )
        for c, t in zip(fcols, ("Owner", "Name", "URL", "Saved")):
            self._fav_tree.heading(c, text=t)
        self._fav_tree.column("url", width=280)
        fsb = ttk.Scrollbar(self._fav_frame, command=self._fav_tree.yview)
        self._fav_tree.configure(yscrollcommand=fsb.set)
        self._fav_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        fsb.pack(side=tk.RIGHT, fill=tk.Y)

        # History
        hcols = ("owner", "name", "commits", "contrib", "at")
        self._hist_tree = ttk.Treeview(
            self._hist_frame, columns=hcols, show="headings", height=12
        )
        for c, t in zip(
            hcols, ("Owner", "Repository", "Commits", "Contributors", "Analyzed at")
        ):
            self._hist_tree.heading(c, text=t)
        hsb = ttk.Scrollbar(self._hist_frame, command=self._hist_tree.yview)
        self._hist_tree.configure(yscrollcommand=hsb.set)
        self._hist_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_lists()

        bf = ttk.Frame(self)
        bf.pack(fill=tk.X, pady=10)
        ttk.Button(bf, text="Back", command=self._back).pack(side=tk.LEFT)
        ttk.Button(bf, text="Open selected (favorites tab)", command=self._open_fav).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(bf, text="Reopen analysis (history tab)", command=self._open_hist).pack(
            side=tk.RIGHT, padx=4
        )

    def _refresh_lists(self) -> None:
        uid = self._app.current_user.id
        self._fav_tree.delete(*self._fav_tree.get_children())
        self._hist_tree.delete(*self._hist_tree.get_children())

        for row in self._app.db.list_favorites(uid):
            self._fav_tree.insert(
                "",
                tk.END,
                values=(
                    row["repo_owner"],
                    row["repo_name"],
                    row["repo_url"] or "—",
                    row["saved_at"][:19].replace("T", " "),
                ),
                tags=(row["repo_owner"], row["repo_name"]),
            )

        for row in self._app.db.list_analysis_history(uid):
            self._hist_tree.insert(
                "",
                tk.END,
                values=(
                    row["repo_owner"],
                    row["repo_name"],
                    row["total_commits"] if row["total_commits"] is not None else "—",
                    row["total_contributors"]
                    if row["total_contributors"] is not None
                    else "—",
                    row["last_analyzed_at"][:19].replace("T", " "),
                ),
                tags=(row["repo_owner"], row["repo_name"]),
            )

    def _back(self) -> None:
        self._app.show_page("dashboard")

    def _repo_from_fav(self, owner: str, name: str) -> Any:
        from models.repository import Repository

        return Repository(
            name=name,
            owner=owner,
            description="",
            visibility="",
            language=None,
            stars=0,
            forks=0,
            updated_at="",
            html_url="",
        )

    def _open_fav(self) -> None:
        sel = self._fav_tree.selection()
        if not sel:
            messagebox.showinfo("Favorites", "Select a favorite row.")
            return
        tags = self._fav_tree.item(sel[0], "tags")
        if len(tags) < 2:
            return
        owner, name = tags[0], tags[1]
        self._run_analysis(self._repo_from_fav(owner, name))

    def _open_hist(self) -> None:
        sel = self._hist_tree.selection()
        if not sel:
            messagebox.showinfo("History", "Select a history row.")
            return
        tags = self._hist_tree.item(sel[0], "tags")
        if len(tags) < 2:
            return
        owner, name = tags[0], tags[1]
        self._run_analysis(self._repo_from_fav(owner, name))

    def _run_analysis(self, repo: Any) -> None:
        from services.github_service import GitHubAPIError
        from services.repository_analyzer import RepositoryAnalyzer

        self._app.set_busy_cursor(True)

        def work() -> None:
            try:
                gh = self._app.get_github_service()
                ana = RepositoryAnalyzer(gh)
                result = ana.analyze(repo.owner, repo.name)
                if result.error_message:
                    self.after(
                        0,
                        lambda: (
                            self._app.set_busy_cursor(False),
                            messagebox.showerror("Analysis", result.error_message),
                        ),
                    )
                    return
                self._app.set_analysis_context(result, repo)

                def done() -> None:
                    self._app.set_busy_cursor(False)
                    self._app.show_page("analysis")

                self.after(0, done)
            except GitHubAPIError as e:
                self.after(
                    0,
                    lambda: (
                        self._app.set_busy_cursor(False),
                        messagebox.showerror("Analysis", str(e)),
                    ),
                )
            except Exception as e:
                self.after(
                    0,
                    lambda: (
                        self._app.set_busy_cursor(False),
                        messagebox.showerror("Analysis", str(e)),
                    ),
                )

        Thread(target=work, daemon=True).start()
