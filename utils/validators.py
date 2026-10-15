"""Small, side-effect-free input validation helpers."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_SKU_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_PATTERN = re.compile(r"^[0-9+(). xX-]{5,40}$")


def validate_sku(value: str) -> str:
    """Return a normalized SKU or raise a readable validation error."""
    sku = value.strip()
    if not _SKU_PATTERN.fullmatch(sku):
        raise ValueError("SKU must be 2–64 characters using letters, numbers, '.', '_' or '-'.")
    return sku


def validate_email(value: str) -> str:
    """Validate a basic email address without claiming full RFC validation."""
    email = value.strip()
    if len(email) > 254 or not _EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Enter a valid email address.")
    return email


def validate_required_text(value: str, field_name: str, maximum_length: int) -> str:
    """Strip and validate required single-line text."""
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} is required.")
    if len(text) > maximum_length:
        raise ValueError(f"{field_name} must be at most {maximum_length} characters.")
    return text


def validate_optional_text(value: str, field_name: str, maximum_length: int) -> str | None:
    """Strip optional text and represent blank values as SQL NULL."""
    text = value.strip()
    if len(text) > maximum_length:
        raise ValueError(f"{field_name} must be at most {maximum_length} characters.")
    return text or None


def validate_phone(value: str) -> str | None:
    """Validate an optional telephone number while allowing common formatting."""
    phone = value.strip()
    if not phone:
        return None
    if not _PHONE_PATTERN.fullmatch(phone):
        raise ValueError("Phone must contain 5–40 digits or common phone formatting characters.")
    if sum(character.isdigit() for character in phone) < 5:
        raise ValueError("Phone must contain at least five digits.")
    return phone


def validate_nonnegative_amount(value: str | int | float | Decimal) -> Decimal:
    """Convert a numeric amount to Decimal and reject negatives or non-finite values."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Amount must be numeric.") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("Amount must be a finite, non-negative number.")
    return amount


def validate_positive_quantity(value: str | int | float | Decimal) -> Decimal:
    """Validate a finite positive stock quantity."""
    quantity = validate_nonnegative_amount(value)
    if quantity == 0:
        raise ValueError("Quantity must be greater than zero.")
    return quantity
