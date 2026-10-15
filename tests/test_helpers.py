from __future__ import annotations

from decimal import Decimal

import pytest

from utils.formatters import format_currency, format_quantity
from utils.validators import validate_email, validate_nonnegative_amount, validate_sku


def test_currency_and_quantity_formatting() -> None:
    assert format_currency(Decimal("1234.5")) == "USD 1,234.50"
    assert format_quantity(Decimal("4.250")) == "4.25"


def test_format_currency_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        format_currency("NaN")


def test_format_currency_rejects_non_numeric_values() -> None:
    with pytest.raises(ValueError, match="numeric"):
        format_currency("not a number")


def test_sku_and_email_validation_normalize_whitespace() -> None:
    assert validate_sku("  SKU_01  ") == "SKU_01"
    assert validate_email("  team@example.com  ") == "team@example.com"


@pytest.mark.parametrize("value", ["A", "bad sku", "bad/value"])
def test_invalid_sku_is_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        validate_sku(value)


def test_amount_validation_returns_decimal_and_rejects_negative() -> None:
    assert validate_nonnegative_amount("12.30") == Decimal("12.30")
    with pytest.raises(ValueError):
        validate_nonnegative_amount("-0.01")
