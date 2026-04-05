"""Main analysis view: metrics, tables, regex filter, charts, exports."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from threading import Thread
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ui.app import App


class RepoAnalysisPage(ttk.Frame):
    """Shows AnalysisResult with filtering and matplotlib visualizations."""

    def __init__(self, parent: tk.Widget, app: App, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)
        self._app = app
        analysis = app.current_analysis
        if not analysis:
            messagebox.showwarning("Analysis", "No analysis loaded.")
            app.show_page("dashboard")
            return

        self._analysis = analysis
        self._repo = app.selected_repo
        self._regex_var = tk.StringVar()
        self._regex_error = tk.StringVar(value="")

        outer = ttk.Frame(self)
        outer.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        body = ttk.Frame(canvas, padding=4)
        cw = canvas.create_window((0, 0), window=body, anchor=tk.NW)

        def _on_configure(_e: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(cw, width=canvas.winfo_width())

        body.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(cw, width=e.width))

        title = (
            f"{analysis.owner}/{analysis.repo_name}"
            if analysis
            else "Repository analysis"
        )
        ttk.Label(body, text=title, style="Header.TLabel").pack(anchor=tk.W)
        if analysis.repo_description:
            ttk.Label(
                body,
                text=(analysis.repo_description[:200] + "…")
                if len(analysis.repo_description or "") > 200
                else (analysis.repo_description or ""),
                wraplength=680,
                foreground="#333",
            ).pack(anchor=tk.W, pady=(0, 6))
        if analysis.github_contributors_endpoint_count is not None:
            ttk.Label(
                body,
                text=(
                    f"GitHub contributors endpoint: {analysis.github_contributors_endpoint_count} "
                    f"(supplementary; distinct authors from commits: {analysis.total_contributors})"
                ),
                wraplength=680,
            ).pack(anchor=tk.W, pady=(0, 4))

        sumf = ttk.LabelFrame(body, text="Summary", padding=8)
        sumf.pack(fill=tk.X, pady=6)
        g = ttk.Frame(sumf)
        g.pack(fill=tk.X)
        self._add_kv(
            g,
            "Total commits",
            str(analysis.total_commits),
            "Contributors",
            str(analysis.total_contributors),
        )
        self._add_kv(
            g,
            "Most active",
            analysis.most_active_contributor or "—",
            "Latest date",
            analysis.latest_commit_date[:19].replace("T", " ")
            if analysis.latest_commit_date
            else "—",
        )
        self._add_kv(
            g,
            "Latest SHA",
            analysis.latest_commit_hash[:12] if analysis.latest_commit_hash else "—",
            "Latest message",
            (analysis.latest_commit_message[:80] + "…")
            if len(analysis.latest_commit_message) > 80
            else (analysis.latest_commit_message or "—"),
        )

        # Contributors table
        cf = ttk.LabelFrame(body, text="Contributor analytics", padding=4)
        cf.pack(fill=tk.BOTH, expand=True, pady=6)
        ccols = (
            "login",
            "name",
            "count",
            "first",
            "last",
            "sha",
            "msg",
        )
        self._contrib_tree = ttk.Treeview(
            cf,
            columns=ccols,
            show="headings",
            height=6,
        )
        heads = (
            "GitHub user",
            "Display",
            "Commits",
            "First commit",
            "Last commit",
            "Latest SHA",
            "Latest message",
        )
        for c, h in zip(ccols, heads):
            self._contrib_tree.heading(c, text=h)
        self._contrib_tree.column("login", width=110)
        self._contrib_tree.column("msg", width=200)
        cs = ttk.Scrollbar(cf, command=self._contrib_tree.yview)
        self._contrib_tree.configure(yscrollcommand=cs.set)
        self._contrib_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cs.pack(side=tk.RIGHT, fill=tk.Y)

        for s in analysis.contributor_stats:
            self._contrib_tree.insert(
                "",
                tk.END,
                values=(
                    s.github_username,
                    s.display_name or "—",
                    s.commit_count,
                    s.first_commit_date[:10] if s.first_commit_date else "—",
                    s.last_commit_date[:10] if s.last_commit_date else "—",
                    s.latest_commit_hash[:10] if s.latest_commit_hash else "—",
                    (s.latest_commit_message[:60] + "…")
                    if len(s.latest_commit_message) > 60
                    else s.latest_commit_message,
                ),
            )

        # Regex panel
        rf = ttk.LabelFrame(body, text="Regex commit filter (message)", padding=6)
        rf.pack(fill=tk.X, pady=6)
        ttk.Label(
            rf,
            text="Pattern (empty = show all). Invalid patterns are caught safely.",
        ).pack(anchor=tk.W)
        row = ttk.Frame(rf)
        row.pack(fill=tk.X, pady=4)
        ttk.Entry(row, textvariable=self._regex_var, width=50).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(row, text="Apply", command=self._apply_regex).pack(
            side=tk.LEFT, padx=6
        )
        presets = ttk.Frame(rf)
        presets.pack(fill=tk.X, pady=4)
        for label in (
            "fix",
            "feat",
            "merge",
            "docs",
            "bug",
        ):
            ttk.Button(
                presets,
                text=label,
                width=10,
                command=lambda p=label: self._set_preset(p),
            ).pack(side=tk.LEFT, padx=2)
        ttk.Label(rf, textvariable=self._regex_error, foreground="#a00").pack(
            anchor=tk.W
        )

        # Commits table
        hf = ttk.LabelFrame(body, text="Commit history (filtered)", padding=4)
        hf.pack(fill=tk.BOTH, expand=True, pady=6)
        hcols = ("sha", "author", "message", "date")
        self._hist_tree = ttk.Treeview(
            hf, columns=hcols, show="headings", height=8
        )
        for c, t in zip(hcols, ("SHA", "Author", "Message", "Date")):
            self._hist_tree.heading(c, text=t)
        self._hist_tree.column("sha", width=90)
        self._hist_tree.column("message", width=320)
        hs = ttk.Scrollbar(hf, command=self._hist_tree.yview)
        self._hist_tree.configure(yscrollcommand=hs.set)
        self._hist_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hs.pack(side=tk.RIGHT, fill=tk.Y)

        self._filtered_commits = list(analysis.commits)
        self._fill_commits()

        # Charts
        chf = ttk.LabelFrame(body, text="Visualizations", padding=4)
        chf.pack(fill=tk.BOTH, expand=True, pady=8)
        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure

            fig = Figure(figsize=(9, 5.5), dpi=100)
            ax1 = fig.add_subplot(2, 2, 1)
            ax2 = fig.add_subplot(2, 2, 2)
            ax3 = fig.add_subplot(2, 2, 3)

            items = sorted(
                analysis.commits_per_contributor.items(),
                key=lambda x: -x[1],
            )[:15]
            if items:
                ax1.barh([x[0][:20] for x in items], [x[1] for x in items])
                ax1.set_xlabel("Commits")
                ax1.set_title("Commits per contributor (top 15)")
                ax1.invert_yaxis()
            days = analysis.commits_per_day
            if days:
                ax2.plot(
                    [d[0] for d in days],
                    [d[1] for d in days],
                    marker=".",
                )
                ax2.set_ylabel("Commits")
                ax2.set_title("Commits over time (UTC days)")
                ax2.tick_params(axis="x", rotation=45)

            cats = {
                k: v
                for k, v in analysis.message_categories.items()
                if k != "other" and v > 0
            }
            if cats:
                ax3.pie(
                    list(cats.values()),
                    labels=list(cats.keys()),
                    autopct="%1.0f%%",
                )
                ax3.set_title("Message categories (heuristic)")

            fig.tight_layout()
            self._canvas = FigureCanvasTkAgg(fig, master=chf)
            self._canvas.draw()
            self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            ttk.Label(
                chf,
                text=f"Charts unavailable: {e}",
                foreground="#a00",
            ).pack()

        # Exports + actions
        xf = ttk.Frame(body)
        xf.pack(fill=tk.X, pady=10)
        ttk.Button(xf, text="Export contributors (CSV)", command=self._exp_csv).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(xf, text="Export full analysis (JSON)", command=self._exp_json).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(xf, text="Export summary (TXT)", command=self._exp_txt).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(xf, text="Conflict-risk analysis", command=self._conflict).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(xf, text="Back", command=self._back).pack(side=tk.RIGHT, padx=4)
        ttk.Button(
            xf,
            text="Dashboard",
            command=lambda: self._app.show_page("dashboard"),
        ).pack(side=tk.RIGHT, padx=4)

    def _add_kv(
        self,
        parent: ttk.Frame,
        a1: str,
        v1: str,
        a2: str,
        v2: str,
    ) -> None:
        r = ttk.Frame(parent)
        r.pack(fill=tk.X, pady=2)
        ttk.Label(r, text=a1 + ":", width=16).pack(side=tk.LEFT)
        ttk.Label(r, text=v1, width=36).pack(side=tk.LEFT)
        ttk.Label(r, text=a2 + ":", width=14).pack(side=tk.LEFT)
        ttk.Label(r, text=v2).pack(side=tk.LEFT)

    def _set_preset(self, p: str) -> None:
        self._regex_var.set(p)
        self._apply_regex()

    def _apply_regex(self) -> None:
        from utils.regex_filter import RegexFilter

        pat = self._regex_var.get()
        filt, err = RegexFilter.filter_commits(self._analysis.commits, pat)
        self._regex_error.set(err or "")
        if err:
            self._filtered_commits = []
        else:
            self._filtered_commits = filt
        self._fill_commits()

    def _fill_commits(self) -> None:
        self._hist_tree.delete(*self._hist_tree.get_children())
        for c in self._filtered_commits:
            self._hist_tree.insert(
                "",
                tk.END,
                values=(
                    c.short_sha,
                    c.author_login,
                    c.message[:120] + ("…" if len(c.message) > 120 else ""),
                    c.committed_at[:19].replace("T", " ") if c.committed_at else "—",
                ),
            )

    def _exp_csv(self) -> None:
        try:
            p = self._app.exporter.export_csv(
                self._analysis.owner,
                self._analysis.repo_name,
                self._analysis.contributor_stats,
            )
            messagebox.showinfo("Export", f"Saved:\n{p}")
        except Exception as e:
            messagebox.showerror("Export", str(e))

    def _exp_json(self) -> None:
        try:
            p = self._app.exporter.export_json(self._analysis, self._app.conflict_risks)
            messagebox.showinfo("Export", f"Saved:\n{p}")
        except Exception as e:
            messagebox.showerror("Export", str(e))

    def _exp_txt(self) -> None:
        try:
            p = self._app.exporter.export_txt(self._analysis, self._app.conflict_risks)
            messagebox.showinfo("Export", f"Saved:\n{p}")
        except Exception as e:
            messagebox.showerror("Export", str(e))

    def _conflict(self) -> None:
        self._app.show_page("conflict")

    def _back(self) -> None:
        self._app.show_page("repo_list")
