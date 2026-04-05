"""Potential conflict-risk findings for the current analysis."""

from __future__ import annotations

from datetime import datetime, timezone

import tkinter as tk
from tkinter import messagebox, ttk
from threading import Thread
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.app import App


class ConflictPage(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: App, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)
        self._app = app
        analysis = app.current_analysis
        if not analysis:
            app.show_page("dashboard")
            return

        ttk.Label(
            self, text="Conflict-risk analysis (heuristic)", style="Header.TLabel"
        ).pack(anchor=tk.W, pady=(0, 6))
        ttk.Label(
            self,
            text=(
                "Inspects recent commits for overlapping file edits by different "
                "authors. This does not run git merge."
            ),
            wraplength=700,
        ).pack(anchor=tk.W)

        rules = ttk.LabelFrame(self, text="Recommendation rules (reference only)", padding=8)
        rules.pack(fill=tk.X, pady=(8, 4))
        ttk.Label(
            rules,
            text=(
                "• Latest commit wins: Git applies merges in commit order; newer commits "
                "are not automatically “right” — coordinate with your team.\n"
                "• Preferred contributor: for high-risk files, consider a single owner "
                "for serial changes.\n"
                "• Manual review recommended: when risk is High or Medium, review diffs "
                "before integrating parallel work."
            ),
            wraplength=700,
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

        self._status = tk.StringVar(value="Loading…")
        ttk.Label(self, textvariable=self._status).pack(anchor=tk.W, pady=6)

        mid = ttk.Frame(self)
        mid.pack(fill=tk.BOTH, expand=True)

        cols = (
            "risk",
            "file",
            "a",
            "b",
            "sha_a",
            "sha_b",
            "date_a",
            "date_b",
            "explain",
            "rec",
        )
        self._tree = ttk.Treeview(
            mid, columns=cols, show="headings", height=16, selectmode="browse"
        )
        heads = (
            "Risk",
            "File",
            "Contributor A",
            "Contributor B",
            "Commit A",
            "Commit B",
            "Date A",
            "Date B",
            "Explanation",
            "Recommendation",
        )
        for c, h in zip(cols, heads):
            self._tree.heading(c, text=h)
        self._tree.column("file", width=180)
        self._tree.column("explain", width=200)
        self._tree.column("rec", width=200)
        sb = ttk.Scrollbar(mid, command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        bf = ttk.Frame(self)
        bf.pack(fill=tk.X, pady=8)
        ttk.Button(bf, text="Back to analysis", command=self._back).pack(side=tk.LEFT)
        ttk.Button(
            bf,
            text="Dashboard",
            command=lambda: self._app.show_page("dashboard"),
        ).pack(side=tk.LEFT, padx=(8, 0))

        self._run_detection()

    def _run_detection(self) -> None:
        analysis = self._app.current_analysis
        if not analysis:
            return

        def work() -> None:
            from services.conflict_detector import ConflictDetector

            try:
                gh = self._app.get_github_service()
                det = ConflictDetector(gh)
                risks = det.detect(
                    analysis.owner,
                    analysis.repo_name,
                    analysis.shas_for_file_inspection,
                )
                user = self._app.current_user
                now = datetime.now(timezone.utc).isoformat()
                if user:
                    for r in risks:
                        try:
                            self._app.db.add_conflict_log(
                                user.id,
                                analysis.repo_name,
                                r.file_path,
                                r.contributor_a,
                                r.contributor_b,
                                r.commit_hash_a,
                                r.commit_hash_b,
                                r.risk_level,
                                now,
                            )
                        except Exception:
                            pass
                self._app.set_analysis_context(
                    analysis, self._app.selected_repo, risks
                )

                def ui() -> None:
                    self._status.set(f"Found {len(risks)} potential risk row(s).")
                    for r in risks:
                        self._tree.insert(
                            "",
                            tk.END,
                            values=(
                                r.risk_level,
                                r.file_path,
                                r.contributor_a,
                                r.contributor_b,
                                r.commit_hash_a[:10],
                                r.commit_hash_b[:10],
                                r.date_a[:19].replace("T", " ") if r.date_a else "—",
                                r.date_b[:19].replace("T", " ") if r.date_b else "—",
                                r.explanation[:100] + ("…" if len(r.explanation) > 100 else ""),
                                r.recommendation[:100]
                                + ("…" if len(r.recommendation) > 100 else ""),
                            ),
                        )

                self.after(0, ui)
            except Exception as e:
                self.after(
                    0,
                    lambda: (
                        self._status.set(""),
                        messagebox.showerror("Conflict analysis", str(e)),
                    ),
                )

        Thread(target=work, daemon=True).start()

    def _back(self) -> None:
        self._app.show_page("analysis")
