"""Reusable custom widgets."""

from __future__ import annotations

import tkinter as tk
from typing import Sequence

import customtkinter as ctk

_COLOR_INVALID = ("#c62828", "#ff6b6b")   # (light, dark)

# Keys that navigate/confirm rather than edit the text: they must not re-filter.
_NON_EDIT_KEYS = {
    "Up", "Down", "Left", "Right", "Home", "End", "Prior", "Next",
    "Return", "KP_Enter", "Escape", "Tab", "ISO_Left_Tab",
    "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
    "Caps_Lock", "Win_L", "Win_R", "App",
}


def filter_options(values: Sequence[str], query: str) -> list[str]:
    """Case-insensitive search: options *starting* with the query come first,
    then options merely *containing* it. Original order is kept in each group."""
    q = query.strip().casefold()
    if not q:
        return list(values)
    starts, contains = [], []
    for value in values:
        folded = value.casefold()
        if folded.startswith(q):
            starts.append(value)
        elif q in folded:
            contains.append(value)
    return starts + contains


def resolve_option(values: Sequence[str], text: str) -> str | None:
    """Return the option exactly matching ``text`` (ignoring case/whitespace), else None."""
    t = text.strip().casefold()
    return next((v for v in values if v.casefold() == t), None)


class FilterComboBox(ctk.CTkFrame):
    """An entry with a drop-down list that filters as you type.

    Keyboard:  type to filter · ↑/↓ move · Enter/Tab pick · Esc close list.
    Mouse:     click an item, or use the ▾ button to browse the full list.

    The chosen value is written to ``variable``. Text that doesn't match an
    option is left as typed and highlighted in red, so the form's validation
    can reject it.
    """

    MAX_VISIBLE_ROWS = 8

    def __init__(self, master, variable: tk.StringVar, values: Sequence[str] = (), **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.variable = variable
        self._values: list[str] = list(values)
        self._matches: list[str] = []
        self._popup: tk.Toplevel | None = None
        self._listbox: tk.Listbox | None = None
        self._scrollbar: ctk.CTkScrollbar | None = None
        self._refocusing = False

        self.grid_columnconfigure(0, weight=1)
        self.entry = ctk.CTkEntry(self, textvariable=variable)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.button = ctk.CTkButton(self, text="▾", width=28, command=self._toggle_full_list)
        self.button.grid(row=0, column=1, padx=(4, 0))
        self._default_border = self.entry.cget("border_color")

        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<Down>", lambda _e: self._move(+1))
        self.entry.bind("<Up>", lambda _e: self._move(-1))
        self.entry.bind("<Return>", self._on_return)
        self.entry.bind("<KP_Enter>", self._on_return)
        self.entry.bind("<Escape>", self._on_escape)
        self.entry.bind("<Tab>", self._on_tab)
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", lambda _e: self.after(150, self._on_focus_lost))
        # Close the list if the main window is moved, resized or minimised.
        self.winfo_toplevel().bind("<Configure>", self._on_window_change, add="+")
        self.winfo_toplevel().bind("<Unmap>", self._on_window_change, add="+")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def set_values(self, values: Sequence[str]) -> None:
        self._values = list(values)
        self._hide()

    def set_state(self, state: str) -> None:
        """``"normal"`` or ``"disabled"``."""
        self.entry.configure(state=state)
        self.button.configure(state=state)
        if state == "disabled":
            self._hide()

    def commit(self) -> str | None:
        """Snap the typed text to the matching option (fixing case) and return it.

        Returns None, and marks the box red, if the text matches no option.
        """
        match = resolve_option(self._values, self.variable.get())
        if match is not None:
            if self.variable.get() != match:
                self.variable.set(match)
            self._set_valid(True)
        else:
            self._set_valid(False)
        return match

    def focus_set(self) -> None:
        self.entry.focus_set()

    def select_range(self, start, end) -> None:
        self.entry.select_range(start, end)

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #
    def _on_key_release(self, event) -> None:
        if event.keysym in _NON_EDIT_KEYS:
            return
        self._refresh()

    def _on_return(self, _event):
        if self._is_open():
            self._pick_highlighted()
            return "break"      # don't let Enter also trigger the form's Save
        self.commit()           # list closed: fall through to the window's Enter = Save
        return None

    def _on_escape(self, _event):
        if self._is_open():
            self._hide()
            return "break"      # don't let Esc also clear the whole form
        return None

    def _on_tab(self, _event):
        if self._is_open() and self._highlighted_index() is not None:
            self._pick_highlighted(refocus=False)
        else:
            self.commit()
        return None             # let Tab move focus to the next field

    def _on_focus_in(self, _event) -> None:
        # Arriving from another field: select everything so typing replaces it.
        if self._refocusing:
            self._refocusing = False
            return
        self.entry.select_range(0, "end")

    def _on_focus_lost(self) -> None:
        if self._focus_is_inside():
            return
        self._hide()
        if self.variable.get().strip():
            self.commit()

    def _on_window_change(self, event) -> None:
        if event.widget is self.winfo_toplevel():
            self._hide()

    def _on_list_click(self, event) -> str:
        if self._listbox is not None and self._matches:
            index = self._listbox.nearest(event.y)
            self._select(self._matches[index])
        return "break"

    def _on_list_hover(self, event) -> None:
        if self._listbox is not None and self._matches:
            self._highlight(self._listbox.nearest(event.y))

    # ------------------------------------------------------------------ #
    # List behaviour
    # ------------------------------------------------------------------ #
    def _refresh(self) -> None:
        matches = filter_options(self._values, self.variable.get())
        self._set_valid(bool(matches))
        if matches:
            self._show(matches)
        else:
            self._hide()

    def _toggle_full_list(self) -> None:
        if self._is_open():
            self._hide()
            return
        self._show(self._values, preselect=self.variable.get())
        self._refocusing = True
        self.entry.focus_set()

    def _move(self, step: int) -> str:
        if not self._is_open():
            matches = filter_options(self._values, self.variable.get()) or self._values
            self._show(matches, preselect=self.variable.get())
            return "break"
        current = self._highlighted_index()
        new = 0 if current is None else max(0, min(len(self._matches) - 1, current + step))
        self._highlight(new)
        return "break"

    def _pick_highlighted(self, refocus: bool = True) -> None:
        index = self._highlighted_index()
        if index is not None:
            self._select(self._matches[index], refocus=refocus)
        else:
            self._hide()

    def _select(self, value: str, refocus: bool = True) -> None:
        self.variable.set(value)
        self._set_valid(True)
        self._hide()
        if refocus:
            self._refocusing = True
            self.entry.focus_set()
            self.entry.icursor("end")

    # ------------------------------------------------------------------ #
    # Popup window
    # ------------------------------------------------------------------ #
    def _ensure_popup(self) -> None:
        if self._popup is not None:
            return
        # A borderless child window, so the list can extend beyond the form.
        popup = tk.Toplevel(self)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_rowconfigure(0, weight=1)

        listbox = tk.Listbox(
            popup, activestyle="none", exportselection=False, takefocus=0,
            borderwidth=0, highlightthickness=0, font=ctk.CTkFont(size=13),
        )
        listbox.grid(row=0, column=0, sticky="nsew", padx=(1, 0), pady=1)
        scrollbar = ctk.CTkScrollbar(popup, command=listbox.yview, width=12)
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.bind("<ButtonRelease-1>", self._on_list_click)
        listbox.bind("<Button-1>", lambda _e: "break")   # keep keyboard focus in the entry
        listbox.bind("<Motion>", self._on_list_hover)

        self._popup, self._listbox, self._scrollbar = popup, listbox, scrollbar

    def _show(self, matches: Sequence[str], preselect: str | None = None) -> None:
        self._ensure_popup()
        assert self._popup and self._listbox and self._scrollbar
        self._matches = list(matches)
        self._apply_colors()

        lb = self._listbox
        lb.delete(0, "end")
        lb.insert("end", *self._matches)
        lb.configure(height=min(len(self._matches), self.MAX_VISIBLE_ROWS))
        if len(self._matches) > self.MAX_VISIBLE_ROWS:
            self._scrollbar.grid(row=0, column=1, sticky="ns", pady=1, padx=(0, 1))
        else:
            self._scrollbar.grid_remove()

        index = 0
        if preselect:
            match = resolve_option(self._matches, preselect)
            if match is not None:
                index = self._matches.index(match)
        self._highlight(index)

        # Position directly under the entry, same width as the whole widget.
        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 2
        width = self.winfo_width()
        self._popup.update_idletasks()
        height = lb.winfo_reqheight() + 2
        self._popup.geometry(f"{width}x{height}+{x}+{y}")
        self._popup.deiconify()
        self._popup.lift()

    def _hide(self) -> None:
        if self._popup is not None and self._is_open():
            self._popup.withdraw()

    def _is_open(self) -> bool:
        return self._popup is not None and bool(self._popup.winfo_viewable())

    def _highlighted_index(self) -> int | None:
        if self._listbox is None:
            return None
        sel = self._listbox.curselection()
        return sel[0] if sel else None

    def _highlight(self, index: int) -> None:
        assert self._listbox is not None
        self._listbox.selection_clear(0, "end")
        self._listbox.selection_set(index)
        self._listbox.see(index)

    def _apply_colors(self) -> None:
        """Match the list to the current light/dark theme."""
        assert self._popup and self._listbox
        i = 1 if ctk.get_appearance_mode() == "Dark" else 0
        theme = ctk.ThemeManager.theme
        pick = lambda c: c[i] if isinstance(c, (list, tuple)) else c  # noqa: E731
        bg = pick(theme["CTkEntry"]["fg_color"])
        fg = pick(theme["CTkEntry"]["text_color"])
        border = pick(theme["CTkEntry"]["border_color"])
        accent = pick(theme["CTkButton"]["fg_color"])
        accent_text = pick(theme["CTkButton"]["text_color"])
        self._popup.configure(bg=border)
        self._listbox.configure(
            bg=bg, fg=fg, selectbackground=accent, selectforeground=accent_text
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _focus_is_inside(self) -> bool:
        try:
            focused = self.focus_get()
        except (KeyError, tk.TclError):
            return False
        if focused is None:
            return False
        me, path = str(self), str(focused)
        return path == me or path.startswith(me + ".")   # popup is our child too

    def _set_valid(self, ok: bool) -> None:
        self.entry.configure(border_color=self._default_border if ok else _COLOR_INVALID)
