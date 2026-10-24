"""Domain model and input parsing/validation (GUI-independent)."""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

from . import config


class ValidationError(ValueError):
    """Raised when user input cannot be turned into a valid Transaction.

    ``field`` names the offending input so the GUI can focus it.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


def parse_date(text: str) -> dt.date:
    """Parse a ``YYYY-MM-DD`` string into a date."""
    text = (text or "").strip()
    if not text:
        raise ValidationError("Date is required.", field="date")
    try:
        return dt.datetime.strptime(text, config.DATE_FORMAT).date()
    except ValueError:
        raise ValidationError(
            f"Invalid date '{text}'. Use the format YYYY-MM-DD.", field="date"
        ) from None


def parse_amount(text: str) -> float:
    """Parse an amount string. Positive = expense, negative = income.

    Accepts a comma as decimal separator (``12,50``) and ignores spaces and
    thousands separators when a dot is also present (``1,234.56``).
    """
    raw = (text or "").strip().replace(" ", "")
    if not raw:
        raise ValidationError("Amount is required.", field="amount")

    if "," in raw and "." in raw:
        raw = raw.replace(",", "")          # 1,234.56 -> 1234.56
    elif "," in raw:
        raw = raw.replace(",", ".")         # 12,50 -> 12.50

    try:
        value = float(raw)
    except ValueError:
        raise ValidationError(
            f"'{text.strip()}' is not a valid number.", field="amount"
        ) from None

    if math.isnan(value) or math.isinf(value):
        raise ValidationError("Amount must be a finite number.", field="amount")
    if value == 0:
        raise ValidationError("Amount cannot be zero.", field="amount")
    return round(value, 2)


@dataclass(frozen=True)
class Options:
    """Allowed dropdown values, loaded from the workbook's lookup sheets.

    The first item of each tuple is the form's default selection.
    """

    currencies: tuple[str, ...]
    payment_methods: tuple[str, ...]
    categories: tuple[str, ...]

    def validate(self, *, currency: str, payment_method: str, category: str) -> None:
        if not category.strip():
            raise ValidationError("Please choose a category.", field="category")
        if currency not in self.currencies:
            raise ValidationError(f"Unknown currency '{currency}'.", field="currency")
        if payment_method not in self.payment_methods:
            raise ValidationError(
                f"Unknown payment method '{payment_method}'.", field="payment_method"
            )
        if category not in self.categories:
            raise ValidationError(
                f"'{category}' is not in your Categories list. Pick one from the list.",
                field="category",
            )


@dataclass(frozen=True)
class Transaction:
    date: dt.date
    amount: float
    currency: str
    payment_method: str
    category: str
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.date, dt.date):
            raise ValidationError("Date must be a date.", field="date")
        for name in ("currency", "payment_method", "category"):
            if not getattr(self, name):
                raise ValidationError(f"{name.replace('_', ' ').capitalize()} is required.", field=name)
        if len(self.description) > config.DESCRIPTION_MAX_LENGTH:
            raise ValidationError(
                f"Description is too long (max {config.DESCRIPTION_MAX_LENGTH} characters).",
                field="description",
            )

    @property
    def is_expense(self) -> bool:
        return self.amount > 0

    @property
    def kind(self) -> str:
        return "Expense" if self.is_expense else "Income"

    @classmethod
    def from_form(
        cls,
        *,
        options: Options,
        date: str,
        amount: str,
        currency: str,
        payment_method: str,
        category: str,
        description: str = "",
    ) -> "Transaction":
        """Build a validated Transaction from raw (string) form values.

        ``options`` holds the allowed dropdown values read from the workbook.
        """
        options.validate(currency=currency, payment_method=payment_method, category=category)
        return cls(
            date=parse_date(date),
            amount=parse_amount(amount),
            currency=currency,
            payment_method=payment_method,
            category=category,
            description=(description or "").strip(),
        )

