"""Locale-neutral formatting helpers used across the application."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


def format_currency(value: Decimal | int | float | str, currency: str = "USD") -> str:
    """Format a monetary value with two decimals and a readable currency code."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Currency value must be numeric.") from exc
    if not amount.is_finite():
        raise ValueError("Currency value must be finite.")
    return f"{currency} {amount:,.2f}"


def format_quantity(value: Decimal | int | float | str) -> str:
    """Format a quantity without redundant trailing fractional zeroes."""
    try:
        quantity = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Quantity must be numeric.") from exc
    if not quantity.is_finite():
        raise ValueError("Quantity must be finite.")
    return f"{quantity:,.3f}".rstrip("0").rstrip(".")
