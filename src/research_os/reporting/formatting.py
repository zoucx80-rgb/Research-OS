from __future__ import annotations


def format_cny(value: int | float | None) -> str | None:
    """Format CNY for human display without changing the stored numeric value."""

    if value is None:
        return None
    amount = float(value)
    absolute = abs(amount)
    if absolute >= 100_000_000:
        return f"{amount / 100_000_000:.2f}亿元"
    if absolute >= 10_000:
        return f"{amount / 10_000:.2f}万元"
    return f"{amount:,.2f}元"
