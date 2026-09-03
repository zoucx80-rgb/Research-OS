from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from research_os.expectations.models import ExpectationGapResult
from research_os.policies import PolicyRegistry, builtin_policy_registry


class SurpriseResult(BaseModel):
    period: str
    net_profit_surprise: float | None = None
    cfo_surprise: float | None = None
    inventory_surprise: float | None = None
    label: str


def _diff(actual, expected, key):
    a = actual.get(key)
    e = expected.get(key)
    return None if a is None or e is None else a - e


def decompose_surprise(actual: dict, expected: dict, period: str) -> SurpriseResult:
    actual_period = actual.get("_period", period)
    expected_period = expected.get("_period", period)
    if actual_period != period or expected_period != period:
        raise ValueError(
            f"period mismatch: actual={actual_period}, expected={expected_period}, requested={period}"
        )
    np = _diff(actual, expected, "net_profit")
    cfo = _diff(actual, expected, "cfo")
    inv = _diff(actual, expected, "inventory")
    if np is not None and np > 0 and cfo is not None and cfo < 0:
        label = "HEADLINE_BEAT_QUALITY_MISS"
    elif np is not None and np > 0:
        label = "HEADLINE_BEAT"
    elif np is not None and np < 0:
        label = "HEADLINE_MISS"
    else:
        label = "MIXED"
    return SurpriseResult(
        period=period,
        net_profit_surprise=np,
        cfo_surprise=cfo,
        inventory_surprise=inv,
        label=label,
    )


def _direction_from_values(market_value: float | None, os_value: float | None) -> str:
    if market_value is None or os_value is None:
        return "MIXED"
    if os_value > market_value:
        return "ABOVE"
    if os_value < market_value:
        return "BELOW"
    return "IN_LINE"


def _direction_from_signals(market_direction: str | None, os_direction: str | None) -> str:
    market = (market_direction or "").upper()
    os_view = (os_direction or "").upper()
    if not market or not os_view:
        return "MIXED"
    if market == os_view:
        return "IN_LINE"
    rank = {"DOWN": -1, "FLAT": 0, "UP": 1}
    if market in rank and os_view in rank:
        return "ABOVE" if rank[os_view] > rank[market] else "BELOW"
    return "MIXED"


def build_expectation_gap(
    *,
    metric: str,
    market: dict[str, Any] | None,
    os_view: float | None = None,
    os_view_direction: str | None = None,
    os_range_low: float | None = None,
    os_range_high: float | None = None,
    os_evidence_ids: list[str] | None = None,
    unit: str | None = None,
    comparison_basis: str | None = None,
    policy_registry: PolicyRegistry | None = None,
) -> ExpectationGapResult | None:
    """Build an expectation gap only when market expectation evidence exists."""

    if not market:
        return None

    market_value = market.get("value")
    market_direction = market.get("direction")
    direction = (
        _direction_from_values(market_value, os_view)
        if market_value is not None and os_view is not None
        else _direction_from_signals(market_direction, os_view_direction)
    )
    magnitude = os_view - market_value if market_value is not None and os_view is not None else None

    limitations: list[str] = []
    policy = policy_registry or builtin_policy_registry()
    minimum_source_count = policy.integer_value("expectation_quality", "minimum_gap_source_count")
    high_quality_source = float(policy.decimal_value("expectation_quality", "high_quality_source"))
    source_count = market.get("source_count")
    source_quality = market.get("source_quality")
    post_event_consensus = market.get("post_event_consensus")
    if source_count is not None and source_count < minimum_source_count:
        limitations.append("市场预期来源数量较少。")
    if source_quality is not None and source_quality < high_quality_source:
        limitations.append("市场预期来源质量有限。")
    if post_event_consensus is False:
        limitations.append("市场预期尚未吸收最近重大事件。")

    evidence_ids = list(
        dict.fromkeys(list(market.get("evidence_ids") or []) + list(os_evidence_ids or []))
    )
    return ExpectationGapResult(
        metric=metric,
        market_value=market_value,
        market_range_low=market.get("range_low"),
        market_range_high=market.get("range_high"),
        market_direction=market_direction,
        os_value=os_view,
        os_range_low=os_range_low,
        os_range_high=os_range_high,
        os_direction=os_view_direction,
        direction=direction,
        magnitude=magnitude,
        unit=unit or market.get("unit"),
        comparison_basis=comparison_basis or market.get("comparison_basis"),
        source_count=source_count,
        source_quality=source_quality,
        age_days=market.get("age_days"),
        post_event_consensus=post_event_consensus,
        limitation=" ".join(limitations) or None,
        evidence_ids=evidence_ids,
        metadata=dict(market.get("metadata") or {}),
    )
