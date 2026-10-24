"""Central, user-editable configuration.

This module holds *settings only* (file location, sheet names, formats,
behaviour). It deliberately contains no personal data: the dropdown options
(currencies, payment methods, categories) are read at runtime from lookup
sheets inside the workbook - see ``money_flow/lookups.py``.
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Override with the MONEYFLOW_DATA_FILE environment variable if you want the
# workbook somewhere else (e.g. a synced OneDrive / Dropbox folder).
DATA_FILE: Path = Path(
    os.environ.get("MONEYFLOW_DATA_FILE", PROJECT_ROOT / "data" / "budget_data.xlsx")
).expanduser()

SHEET_NAME: str = "Transactions"

# --------------------------------------------------------------------------- #
# Lookup sheets (dropdown options)
# --------------------------------------------------------------------------- #
# Each sheet lists one option per row in column A, starting at row 1 (no
# header). Blank cells are skipped and duplicates are ignored. The FIRST entry
# of each sheet is used as the default selection in the form.
CURRENCIES_SHEET: str = "Currencies"
PAYMENT_METHODS_SHEET: str = "Payment_methods"
CATEGORIES_SHEET: str = "Categories"

# --------------------------------------------------------------------------- #
# Formats & behaviour
# --------------------------------------------------------------------------- #
DATE_FORMAT: str = "%Y-%m-%d"           # format used in the GUI input
EXCEL_DATE_FORMAT: str = "yyyy-mm-dd"   # number format applied in Excel
EXCEL_AMOUNT_FORMAT: str = "#,##0.00"

DESCRIPTION_MAX_LENGTH: int = 200

# After a successful save, keep the currency / payment method / category the
# user picked (handy when entering a batch of similar transactions). Set to
# False to reset every field to its default.
KEEP_SELECTIONS_AFTER_SAVE: bool = True

# GUI appearance: "light", "dark" or "system".
APPEARANCE_MODE: str = "system"
COLOR_THEME: str = "blue"

