"""EUR amounts: integer cents in storage; legacy integers mean whole euros."""
from decimal import Decimal, InvalidOperation
from typing import Annotated
from pydantic import BeforeValidator


def euros(value):
    if isinstance(value, bool):
        raise ValueError("Invalid EUR amount")
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or not 0 <= amount <= 1_000_000 or amount * 100 != (amount * 100).to_integral_value():
            raise ValueError("EUR prices need at most two decimal places, from 0 to 1000000")
        return amount
    except (InvalidOperation, TypeError):
        raise ValueError("Invalid EUR amount") from None

EuroAmount = Annotated[Decimal, BeforeValidator(euros)]


def cents(value):
    return int(euros(value) * 100)


def stored_cents(document):
    if "price_cents" in document:
        value = document["price_cents"]
        if type(value) is not int or not 0 <= value <= 100_000_000 or document.get("currency", "EUR") != "EUR":
            raise ValueError("Invalid catalog price")
        return value
    return cents(document["price"])


def public_money(document):
    value = stored_cents(document)
    document.update(price_cents=value, currency="EUR", price=f"{value // 100}.{value % 100:02d}")
    return document
