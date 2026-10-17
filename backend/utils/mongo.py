"""
Shared MongoDB query-fragment helpers.
"""
import re
from .money import cents


def case_insensitive_exact(value: str) -> dict:
    """Query fragment for an exact, case-insensitive string match."""
    return {"$regex": f"^{re.escape(value)}$", "$options": "i"}


def case_insensitive_contains(value: str) -> dict:
    """Query fragment for a case-insensitive substring match."""
    return {"$regex": re.escape(value), "$options": "i"}


def price_range_filter(min_price=None, max_price=None) -> dict:
    """Match canonical cents and legacy whole-EUR documents, inclusively."""
    canonical, legacy = {}, {}
    if min_price is not None:
        value = cents(min_price)
        canonical["$gte"] = value
        legacy["$gte"] = (value + 99) // 100
    if max_price is not None:
        value = cents(max_price)
        canonical["$lte"] = value
        legacy["$lte"] = value // 100
    if not canonical:
        return {}
    return {"$or": [{"price_cents": canonical},
                    {"price_cents": {"$exists": False}, "price": legacy}]}
