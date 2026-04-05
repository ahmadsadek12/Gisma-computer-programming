"""Local account registration."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.app import App


class SignUpPage(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: App, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)
        self._app = app

        ttk.Label(self, text="Create account", style="Header.TLabel").pack(
            anchor=tk.W, pady=(0, 12)
        )

        form = ttk.Frame(self)
        form.pack(fill=tk.X)

        self._user = tk.StringVar()
        self._email = tk.StringVar()
        self._pw = tk.StringVar()
        self._pw2 = tk.StringVar()

        self._row(form, "Username", self._user)
        self._row(form, "Email", self._email)
        self._row(form, "Password", self._pw, show="*")
        self._row(form, "Confirm password", self._pw2, show="*")

        bf = ttk.Frame(self)
        bf.pack(fill=tk.X, pady=16)
        ttk.Button(bf, text="Back", command=self._back).pack(side=tk.LEFT)
        ttk.Button(bf, text="Submit", command=self._submit).pack(side=tk.RIGHT)

    def _row(
        self, parent: ttk.Frame, label: str, var: tk.StringVar, show: str = ""
    ) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var, width=40, show=show).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

    def _back(self) -> None:
        self._app.show_page("welcome")

    def _submit(self) -> None:
        try:
            user = self._app.auth.signup(
                self._user.get(),
                self._email.get(),
                self._pw.get(),
                self._pw2.get(),
            )
            self._app.set_user(user)
            messagebox.showinfo("Success", "Account created. You are now logged in.")
            self._app.show_page("dashboard")
        except ValueError as e:
            messagebox.showerror("Sign up", str(e))
        except RuntimeError as e:
            messagebox.showerror("Sign up", str(e))
