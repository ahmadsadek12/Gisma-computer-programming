"""List repositories with search, analyze, and favorite toggles."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from threading import Thread
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.app import App


class RepoListPage(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: App, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)
        self._app = app

        if not app.current_user:
            app.show_page("welcome")
            return

        ttk.Label(self, text="Your repositories", style="Header.TLabel").pack(
            anchor=tk.W, pady=(0, 4)
        )
        ttk.Label(
            self,
            text="Double-click a row to analyze, or select and click Analyze. Use Favorite to toggle ★.",
            foreground="#444",
        ).pack(anchor=tk.W, pady=(0, 6))

        top = ttk.Frame(self)
        top.pack(fill=tk.X, pady=(0, 8))
        self._search = tk.StringVar()
        self._search.trace_add("write", lambda *_a: self._apply_filter())
        ttk.Label(top, text="Search (repo name):").pack(side=tk.LEFT)
        ttk.Entry(top, textvariable=self._search, width=36).pack(
            side=tk.LEFT, padx=8
        )
        ttk.Button(top, text="Refresh", command=self._load).pack(side=tk.LEFT)

        # Tree columns: name, language, visibility, stars, updated, owner, description, forks.
        cols = (
            "name",
            "language",
            "visibility",
            "stars",
            "updated",
            "owner",
            "description",
            "forks",
        )
        mid = ttk.Frame(self)
        mid.pack(fill=tk.BOTH, expand=True)
        self._tree = ttk.Treeview(
            mid, columns=cols, show="headings", height=14, selectmode="browse"
        )
        headings = (
            "Repository",
            "Language",
            "Visibility",
            "Stars",
            "Updated",
            "Owner",
            "Description",
            "Forks",
        )
        for c, w in zip(cols, headings):
            self._tree.heading(c, text=w)
        self._tree.column("name", width=200)
        self._tree.column("language", width=90)
        self._tree.column("visibility", width=80)
        self._tree.column("stars", width=50)
        self._tree.column("updated", width=110)
        self._tree.column("owner", width=110)
        self._tree.column("description", width=200)
        self._tree.column("forks", width=50)

        scroll = ttk.Scrollbar(mid, orient=tk.VERTICAL, command=self._tree.yview)
        xscroll = ttk.Scrollbar(mid, orient=tk.HORIZONTAL, command=self._tree.xview)
        self._tree.configure(
            yscrollcommand=scroll.set, xscrollcommand=xscroll.set
        )
        self._tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        mid.grid_rowconfigure(0, weight=1)
        mid.grid_columnconfigure(0, weight=1)

        self._tree.bind("<Double-1>", lambda _e: self._analyze())

        self._all_rows: list[tuple[str, ...]] = []
        self._repo_by_name: dict[str, object] = {}

        bf = ttk.Frame(self)
        bf.pack(fill=tk.X, pady=10)
        ttk.Button(bf, text="Back", command=self._back).pack(side=tk.LEFT)
        ttk.Button(bf, text="Analyze", command=self._analyze).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(bf, text="Favorite / Unfavorite", command=self._fav).pack(
            side=tk.RIGHT, padx=4
        )

        self._load_async()

    def _back(self) -> None:
        self._app.show_page("dashboard")

    def _load_async(self) -> None:
        def work() -> None:
            try:
                try:
                    gh = self._app.get_github_service()
                except RuntimeError as e:
                    self.after(
                        0,
                        lambda: (
                            self._app.set_busy_cursor(False),
                            messagebox.showerror("GitHub", str(e)),
                        ),
                    )
                    return
                repos = gh.list_repositories()
                self._app.set_repos_cache(repos)

                def ui() -> None:
                    self._all_rows.clear()
                    self._repo_by_name.clear()
                    uid = self._app.current_user.id
                    for r in repos:
                        fav = "★" if self._app.db.is_favorite(uid, r.name, r.owner) else ""
                        key = f"{r.owner}/{r.name}"
                        self._repo_by_name[key] = r
                        desc = (r.description or "").replace("\n", " ").strip()
                        if len(desc) > 80:
                            desc = desc[:77] + "…"
                        self._all_rows.append(
                            (
                                f"{fav} {r.name}",
                                r.language or "—",
                                r.visibility,
                                str(r.stars),
                                r.updated_at[:10] if r.updated_at else "—",
                                r.owner,
                                desc or "—",
                                str(r.forks),
                                r.owner,
                                r.name,
                            )
                        )
                    self._apply_filter()
                    self._app.set_busy_cursor(False)

                self.after(0, ui)
            except Exception as e:
                self.after(
                    0,
                    lambda: (
                        self._app.set_busy_cursor(False),
                        messagebox.showerror("Repositories", str(e)),
                    ),
                )

        self._app.set_busy_cursor(True)
        Thread(target=work, daemon=True).start()

    def _load(self) -> None:
        self._load_async()

    def _apply_filter(self) -> None:
        """Filter rows by repository name substring."""
        q = self._search.get().lower().strip()
        self._tree.delete(*self._tree.get_children())
        for row in self._all_rows:
            repo_only = row[0].replace("★ ", "").replace("★", "").strip()
            if not q or q in repo_only.lower():
                self._tree.insert(
                    "",
                    tk.END,
                    values=row[:8],
                    tags=(row[8], row[9]),
                )

    def _selected_repo(self) -> object | None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Repositories", "Select a repository row first.")
            return None
        tags = self._tree.item(sel[0], "tags")
        if len(tags) >= 2:
            key = f"{tags[0]}/{tags[1]}"
            return self._repo_by_name.get(key)
        return None

    def _analyze(self) -> None:
        r = self._selected_repo()
        if not r:
            return

        from services.github_service import GitHubAPIError
        from services.repository_analyzer import RepositoryAnalyzer

        self._app.set_busy_cursor(True)
        self.update_idletasks()

        def work() -> None:
            try:
                gh = self._app.get_github_service()
                ana = RepositoryAnalyzer(gh)
                result = ana.analyze(r.owner, r.name)
                if result.error_message:
                    self.after(
                        0,
                        lambda: messagebox.showerror("Analysis", result.error_message),
                    )
                    self.after(0, lambda: self._app.set_busy_cursor(False))
                    return
                user = self._app.current_user
                if user:
                    from datetime import datetime, timezone

                    self._app.db.add_analysis_history(
                        user.id,
                        r.name,
                        r.owner,
                        result.total_commits,
                        result.total_contributors,
                        datetime.now(timezone.utc).isoformat(),
                    )
                self._app.set_analysis_context(result, r)

                def go() -> None:
                    self._app.set_busy_cursor(False)
                    self._app.show_page("analysis")

                self.after(0, go)
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

    def _fav(self) -> None:
        r = self._selected_repo()
        if not r or not self._app.current_user:
            return
        from datetime import datetime, timezone

        uid = self._app.current_user.id
        try:
            if self._app.db.is_favorite(uid, r.name, r.owner):
                self._app.db.remove_favorite(uid, r.name, r.owner)
            else:
                self._app.db.add_favorite(
                    uid,
                    r.name,
                    r.owner,
                    r.html_url,
                    datetime.now(timezone.utc).isoformat(),
                )
            self._load_async()
        except Exception as e:
            messagebox.showerror("Favorite", str(e))
