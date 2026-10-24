# Money Flow 💸

A lightweight personal budget manager. Transactions are entered through a small
desktop form and persisted to an Excel workbook (`data/budget_data.xlsx`) that
acts as a flat-file database.

## Project structure

```
money-flow/
├── main.py                  # Entry point - launches the GUI
├── requirements.txt         # Runtime deps (customtkinter, pandas, openpyxl)
├── requirements-dev.txt     # + pytest
├── pyproject.toml           # Project metadata / pytest config
├── data/
│   └── budget_data.xlsx     # Created automatically on first run (git-ignored)
├── money_flow/
│   ├── config.py            # ⚙️ Settings only: file path, sheet names, formats (no personal data)
│   ├── models.py            # Transaction + Options dataclasses, parsing/validation
│   ├── lookups.py           # Reads dropdown options from the workbook's lookup sheets
│   ├── storage.py           # ExcelStorage: create / append / read the workbook
│   └── gui/
│       ├── app.py           # customtkinter entry form
│       └── widgets.py       # FilterComboBox: search-as-you-type category picker
└── tests/
    └── test_storage.py      # Unit tests for parsing + storage (no GUI)
```

Layers depend in one direction only: `gui → models / storage → config`.
The GUI holds no business logic, so later phases (reports, charts, CLI import)
can reuse `models` and `storage` unchanged.

## Quickstart

**Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

> Linux only: if you get `No module named '_tkinter'`, install Tk via your
> package manager (e.g. `sudo apt install python3-tk`).

Run tests:
```bash
pip install -r requirements-dev.txt
pytest
```

## Usage

| Field          | Notes                                                       |
|----------------|-------------------------------------------------------------|
| Date           | `YYYY-MM-DD`, defaults to today (**Today** button resets it) |
| Amount         | **Positive = expense**, **negative = income**. `12,50` is accepted too. |
| Currency       | From the `Currencies` sheet                                 |
| Payment Method | From the `Payment_methods` sheet                            |
| Category       | From the `Categories` sheet. **Type to filter** (e.g. `tes` → Tesco), ↑/↓ to move, Enter/Tab or click to pick, ▾ to browse all |
| Description    | Optional, max 200 chars                                     |

Keyboard: **Enter** saves, **Esc** clears the form. While the category list is
open, Enter/Esc act on the list instead (pick / close), so a fast flow is:
type `tes` → **Enter** (picks Tesco) → **Enter** (saves).

After saving, date/amount/description are reset; currency, payment method and
category are kept for quick batch entry (toggle with
`KEEP_SELECTIONS_AFTER_SAVE` in `config.py`).

## Customising

### Dropdown options live in the workbook

Currencies, payment methods and categories are **not** in the code. They are
read from three sheets inside `budget_data.xlsx`:

| Sheet             | Content                                  |
|-------------------|------------------------------------------|
| `Currencies`      | one currency per row, column A           |
| `Payment_methods` | one payment method per row, column A     |
| `Categories`      | one category per row, column A           |

- Start at row 1, with no header row. Blank cells are skipped and duplicates ignored.
- The **first row** of each sheet is the default selection in the form.
- After editing a sheet, click **↻ Reload lists** in the app (no restart needed).
- The sheet names can be changed in `config.py` (`*_SHEET` settings).
- On first run with no workbook, the app creates one with these three sheets
  empty and asks you to fill them in.

### Settings

Edit [`money_flow/config.py`](money_flow/config.py) (settings only, no personal data):

- `DATA_FILE` - or set the `MONEYFLOW_DATA_FILE` env var to store the workbook
  elsewhere (e.g. a synced cloud folder).
- `KEEP_SELECTIONS_AFTER_SAVE`, formats, appearance.

## Privacy

`budget_data.xlsx` contains personal financial data and is **never committed**:
`.gitignore` excludes every `*.xlsx` / `*.xlsm` / `*.xls` file in the repo, plus
Excel lock files (`~$*`) and the app's temp files. To double-check:

```bash
git check-ignore -v data/budget_data.xlsx   # should print the matching rule
git ls-files "*.xlsx"                       # should print nothing
```

## Safety notes

- Rows are inserted with openpyxl in descending date order (newest at the top),
  so existing data, formatting and any extra sheets you add are preserved.
- Saves are atomic (write to temp file → swap), so a crash can't corrupt the
  workbook.
- If the workbook is open in Excel, the app shows a warning and nothing is
  written - close Excel and press Save again; your form input is kept.
- The header row is checked on every write; if the columns don't match the
  expected schema the app refuses to write rather than misaligning data.

