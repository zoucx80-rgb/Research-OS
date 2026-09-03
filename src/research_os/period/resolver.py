from __future__ import annotations

from .models import ReportingPeriod


def resolve_period_days(period: ReportingPeriod) -> int | None:
    if period.period_days is not None:
        return period.period_days
    if period.period_start is not None and period.period_end is not None:
        return (period.period_end - period.period_start).days + 1
    if period.period_type == "FY":
        return 365
    return None


def turnover_days(
    avg_balance: float | None, flow: float | None, period: ReportingPeriod
) -> float | None:
    days = resolve_period_days(period)
    if avg_balance is None or flow is None or flow == 0 or days is None:
        return None
    return float(avg_balance) / float(flow) * days


def period_turns(flow: float | None, avg_balance: float | None) -> float | None:
    if flow is None or avg_balance is None or avg_balance == 0:
        return None
    return float(flow) / float(avg_balance)


def annualized_turns(
    flow: float | None,
    avg_balance: float | None,
    period: ReportingPeriod,
    *,
    annual_days: int = 365,
) -> float | None:
    turns = period_turns(flow, avg_balance)
    days = resolve_period_days(period)
    if turns is None or days is None or days == 0:
        return None
    return turns * annual_days / days
