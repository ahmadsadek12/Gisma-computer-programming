"""Local login."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.app import App


class LoginPage(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: App, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)
        self._app = app

        ttk.Label(self, text="Log in", style="Header.TLabel").pack(
            anchor=tk.W, pady=(0, 12)
        )

        form = ttk.Frame(self)
        form.pack(fill=tk.X)

        self._ident = tk.StringVar()
        self._pw = tk.StringVar()

        row = ttk.Frame(form)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Username or email", width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self._ident, width=40).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

        row2 = ttk.Frame(form)
        row2.pack(fill=tk.X, pady=4)
        ttk.Label(row2, text="Password", width=18).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self._pw, width=40, show="*").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

        bf = ttk.Frame(self)
        bf.pack(fill=tk.X, pady=16)
        ttk.Button(bf, text="Back", command=self._back).pack(side=tk.LEFT)
        ttk.Button(bf, text="Log In", command=self._go).pack(side=tk.RIGHT)

        link = ttk.Frame(self)
        link.pack(fill=tk.X, pady=8)
        ttk.Label(link, text="No account?").pack(side=tk.LEFT)
        ttk.Button(link, text="Sign up", command=self._signup).pack(side=tk.LEFT, padx=6)

    def _back(self) -> None:
        self._app.show_page("welcome")

    def _signup(self) -> None:
        self._app.show_page("signup")

    def _go(self) -> None:
        try:
            user = self._app.auth.login(self._ident.get(), self._pw.get())
            self._app.set_user(user)
            self._app.show_page("dashboard")
        except ValueError as e:
            messagebox.showerror("Login", str(e))
