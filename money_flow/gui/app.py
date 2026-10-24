"""Transaction entry window."""

from __future__ import annotations

import datetime as dt
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from .. import config
from ..lookups import load_options
from ..models import Options, Transaction, ValidationError, parse_amount
from ..storage import ExcelStorage, FileLockedError, StorageError
from .widgets import FilterComboBox

_COLOR_OK = ("#1e7e34", "#39a755")       # (light, dark)
_COLOR_ERR = ("#c62828", "#ff6b6b")
_COLOR_MUTED = ("gray40", "gray65")
_COLOR_EXPENSE = ("#c62828", "#ff8a80")
_COLOR_INCOME = ("#1e7e34", "#69f0ae")

_STATUS_CLEAR_MS = 5000


class TransactionApp(ctk.CTk):
    def __init__(self, storage: ExcelStorage | None = None) -> None:
        super().__init__()
        self.storage = storage or ExcelStorage()
        self.options: Options | None = None   # loaded from the workbook's lookup sheets
        self._status_job: str | None = None

        self.title("Money Flow - New Transaction")
        self.minsize(460, 0)
        self.resizable(True, False)

        self._build_vars()
        self._build_form()
        self._bind_shortcuts()
        self.reset_form(full=True)

        # Initialise the workbook once the window is up so errors can be shown.
        self.after(50, self._init_storage)

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _build_vars(self) -> None:
        self.date_var = tk.StringVar()
        self.amount_var = tk.StringVar()
        self.currency_var = tk.StringVar()
        self.payment_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self.amount_var.trace_add("write", lambda *_: self._update_amount_hint())

    def _build_form(self) -> None:
        pad = {"padx": 16, "pady": 6}
        form = ctk.CTkFrame(self)
        form.pack(fill="both", expand=True, padx=16, pady=(16, 8))
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="New Transaction", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(14, 10)
        )

        # Date
        self._label(form, "Date", 1)
        self.date_entry = ctk.CTkEntry(form, textvariable=self.date_var, placeholder_text="YYYY-MM-DD")
        self.date_entry.grid(row=1, column=1, sticky="ew", **pad)
        ctk.CTkButton(form, text="Today", width=70, command=self._set_today).grid(
            row=1, column=2, sticky="e", padx=(0, 16), pady=6
        )

        # Amount
        self._label(form, "Amount", 2)
        self.amount_entry = ctk.CTkEntry(form, textvariable=self.amount_var, placeholder_text="e.g. 12.50 or -2500")
        self.amount_entry.grid(row=2, column=1, sticky="ew", **pad)
        self.amount_hint = ctk.CTkLabel(form, text="", width=70, anchor="e")
        self.amount_hint.grid(row=2, column=2, sticky="e", padx=(0, 16))
        ctk.CTkLabel(
            form,
            text="Positive = expense  ·  Negative = income",
            text_color=_COLOR_MUTED,
            font=ctk.CTkFont(size=11),
        ).grid(row=3, column=1, columnspan=2, sticky="w", padx=16, pady=(0, 4))

        # Dropdowns (values are filled in from the workbook by _apply_options)
        self.currency_menu = self._option(form, "Currency", 4, self.currency_var)
        self.payment_menu = self._option(form, "Payment Method", 5, self.payment_var)

        # Category: long list, so a search-as-you-type box instead of a plain dropdown
        self._label(form, "Category", 6)
        self.category_box = FilterComboBox(form, variable=self.category_var)
        self.category_box.grid(row=6, column=1, columnspan=2, sticky="ew", padx=16, pady=6)
        self.category_box.set_state("disabled")

        # Description
        self._label(form, "Description", 7)
        self.description_entry = ctk.CTkEntry(
            form, textvariable=self.description_var, placeholder_text="Optional note"
        )
        self.description_entry.grid(row=7, column=1, columnspan=2, sticky="ew", **pad)

        # Buttons
        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=8, column=0, columnspan=3, sticky="ew", padx=16, pady=(12, 14))
        buttons.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            buttons, text="↻ Reload lists", width=110, fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"), command=self._load_options,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            buttons, text="Clear", width=100, fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"), command=lambda: self.reset_form(full=True),
        ).grid(row=0, column=1, padx=(0, 8))
        self.save_button = ctk.CTkButton(buttons, text="Save  (Enter)", width=140, command=self.save)
        self.save_button.grid(row=0, column=2)

        # Status + footer
        self.status_label = ctk.CTkLabel(self, text="", anchor="w", wraplength=440, justify="left")
        self.status_label.pack(fill="x", padx=20)
        ctk.CTkLabel(
            self, text=f"File: {self.storage.path}", anchor="w", text_color=_COLOR_MUTED,
            font=ctk.CTkFont(size=10), wraplength=440, justify="left",
        ).pack(fill="x", padx=20, pady=(0, 12))

    @staticmethod
    def _label(parent, text: str, row: int) -> None:
        ctk.CTkLabel(parent, text=text, anchor="w").grid(row=row, column=0, sticky="w", padx=16, pady=6)

    def _option(self, parent, text: str, row: int, var: tk.StringVar) -> ctk.CTkOptionMenu:
        self._label(parent, text, row)
        menu = ctk.CTkOptionMenu(
            parent, variable=var, values=["Loading…"], dynamic_resizing=False, state="disabled"
        )
        menu.grid(row=row, column=1, columnspan=2, sticky="ew", padx=16, pady=6)
        return menu

    def _bind_shortcuts(self) -> None:
        self.bind("<Return>", lambda _e: self.save())
        self.bind("<KP_Enter>", lambda _e: self.save())
        self.bind("<Escape>", lambda _e: self.reset_form(full=True))

    # ------------------------------------------------------------------ #
    # Behaviour
    # ------------------------------------------------------------------ #
    def _init_storage(self) -> None:
        try:
            created = self.storage.ensure_exists()
        except FileLockedError as exc:
            messagebox.showwarning("Spreadsheet in use", str(exc), parent=self)
            self._set_status("Spreadsheet is locked - close it before saving.", error=True)
            return
        except StorageError as exc:
            messagebox.showerror("Storage error", str(exc), parent=self)
            self._set_status("Storage error - see details above.", error=True)
            return
        if created:
            self._set_status(f"Created new database: {self.storage.path.name}")
        self._load_options(announce=False)

    def _load_options(self, announce: bool = True) -> None:
        """(Re)read the dropdown options from the workbook's lookup sheets."""
        try:
            options = load_options(self.storage.path)
        except StorageError as exc:
            messagebox.showerror("Dropdown options", str(exc), parent=self)
            self._set_status(
                "Dropdown lists could not be loaded - fix the workbook, then click Reload lists.",
                error=True,
            )
            return
        self._apply_options(options)
        if announce:
            self._set_status(
                f"Lists reloaded: {len(options.currencies)} currencies, "
                f"{len(options.payment_methods)} payment methods, "
                f"{len(options.categories)} categories."
            )

    def _apply_options(self, options: Options) -> None:
        self.options = options
        for menu, var, values in (
            (self.currency_menu, self.currency_var, options.currencies),
            (self.payment_menu, self.payment_var, options.payment_methods),
        ):
            menu.configure(values=list(values), state="normal")
            if var.get() not in values:   # keep the current pick if it still exists
                var.set(values[0])
        self.category_box.set_values(options.categories)
        self.category_box.set_state("normal")
        if self.category_var.get() not in options.categories:
            self.category_var.set(options.categories[0])

    def _set_today(self) -> None:
        self.date_var.set(dt.date.today().strftime(config.DATE_FORMAT))

    def _update_amount_hint(self) -> None:
        try:
            value = parse_amount(self.amount_var.get())
        except ValidationError:
            self.amount_hint.configure(text="")
            return
        if value > 0:
            self.amount_hint.configure(text="Expense", text_color=_COLOR_EXPENSE)
        else:
            self.amount_hint.configure(text="Income", text_color=_COLOR_INCOME)

    def reset_form(self, full: bool = False) -> None:
        """Reset inputs. ``full`` also resets dropdowns regardless of config."""
        self._set_today()
        self.amount_var.set("")
        self.description_var.set("")
        if (full or not config.KEEP_SELECTIONS_AFTER_SAVE) and self.options is not None:
            # Defaults = first entry of each lookup sheet.
            self.currency_var.set(self.options.currencies[0])
            self.payment_var.set(self.options.payment_methods[0])
            self.category_var.set(self.options.categories[0])
        self.amount_entry.focus_set()

    def save(self) -> None:
        if self.options is None:
            self._set_status(
                "Cannot save: dropdown lists are not loaded. Fix the workbook and click Reload lists.",
                error=True,
            )
            self.bell()
            return
        self.category_box.commit()   # e.g. typed "tesco" -> "Tesco"
        try:
            txn = Transaction.from_form(
                options=self.options,
                date=self.date_var.get(),
                amount=self.amount_var.get(),
                currency=self.currency_var.get(),
                payment_method=self.payment_var.get(),
                category=self.category_var.get(),
                description=self.description_var.get(),
            )
        except ValidationError as exc:
            self._set_status(str(exc), error=True)
            self._focus_field(exc.field)
            self.bell()
            return

        self.save_button.configure(state="disabled")
        try:
            row = self.storage.append(txn)
        except FileLockedError as exc:
            messagebox.showwarning("Spreadsheet in use", str(exc), parent=self)
            self._set_status("Not saved - spreadsheet is open elsewhere.", error=True)
            return
        except StorageError as exc:
            messagebox.showerror("Could not save", str(exc), parent=self)
            self._set_status("Not saved - see error details.", error=True)
            return
        finally:
            self.save_button.configure(state="normal")

        self._set_status(
            f"✔ Saved {txn.kind.lower()}: {abs(txn.amount):,.2f} {txn.currency} · "
            f"{txn.category} · {txn.date:%Y-%m-%d} (row {row})"
        )
        self.reset_form()

    def _focus_field(self, field: str | None) -> None:
        widget = {
            "date": self.date_entry,
            "amount": self.amount_entry,
            "category": self.category_box,
            "description": self.description_entry,
        }.get(field or "")
        if widget is not None:
            widget.focus_set()
            widget.select_range(0, "end")

    def _set_status(self, message: str, error: bool = False) -> None:
        self.status_label.configure(text=message, text_color=_COLOR_ERR if error else _COLOR_OK)
        if self._status_job:
            self.after_cancel(self._status_job)
        self._status_job = self.after(
            _STATUS_CLEAR_MS * (2 if error else 1),
            lambda: self.status_label.configure(text=""),
        )


def run() -> int:
    ctk.set_appearance_mode(config.APPEARANCE_MODE)
    ctk.set_default_color_theme(config.COLOR_THEME)
    app = TransactionApp()
    app.mainloop()
    return 0

