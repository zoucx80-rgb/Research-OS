from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field


UNIT_FACTORS = {
    "元": 1.0,
    "千元": 1_000.0,
    "万元": 10_000.0,
    "百万元": 1_000_000.0,
    "亿元": 100_000_000.0,
}


def normalize_to_yuan(value: float, unit: str) -> float:
    try:
        factor = UNIT_FACTORS[unit]
    except KeyError as exc:
        raise ValueError(f"unsupported financial unit: {unit}") from exc
    return float(value) * factor


class FinancialMetricObservation(BaseModel):
    metric: str
    period: str
    scope: str = "consolidated"
    version: str = "reported"
    value: float
    unit: str
    evidence_ids: list[str] = Field(default_factory=list)

    @property
    def normalized_value(self) -> float:
        return normalize_to_yuan(self.value, self.unit)


class FinancialSanityResult(BaseModel):
    status: Literal["PASS", "FAIL"]
    errors: list[str] = Field(default_factory=list)
    expected_value: float | None = None
    actual_value: float | None = None
    normalized_metrics: dict[str, float] = Field(default_factory=dict)


def _matches(expected: float, actual: float, *, rel_tol: float = 1e-6, abs_tol: float = 1e-6) -> bool:
    return math.isclose(expected, actual, rel_tol=rel_tol, abs_tol=abs_tol)


def _result(expected: float, actual: float, label: str, *, rel_tol: float = 1e-6, abs_tol: float = 1e-6) -> FinancialSanityResult:
    if _matches(expected, actual, rel_tol=rel_tol, abs_tol=abs_tol):
        return FinancialSanityResult(status="PASS", expected_value=expected, actual_value=actual)
    return FinancialSanityResult(
        status="FAIL",
        errors=[f"{label} mismatch: expected {expected}, got {actual}"],
        expected_value=expected,
        actual_value=actual,
    )


class FinancialSanityValidator:
    def check_gross_profit(
        self,
        *,
        revenue: float,
        revenue_unit: str,
        cogs: float,
        cogs_unit: str,
        declared_gross_profit: float,
        declared_unit: str,
    ) -> FinancialSanityResult:
        expected = normalize_to_yuan(revenue, revenue_unit) - normalize_to_yuan(cogs, cogs_unit)
        actual = normalize_to_yuan(declared_gross_profit, declared_unit)
        return _result(expected, actual, "gross profit")

    def check_gross_margin(
        self,
        *,
        revenue: float,
        revenue_unit: str,
        gross_profit: float,
        gross_profit_unit: str,
        declared_margin: float,
    ) -> FinancialSanityResult:
        normalized_revenue = normalize_to_yuan(revenue, revenue_unit)
        normalized_profit = normalize_to_yuan(gross_profit, gross_profit_unit)
        if normalized_revenue == 0:
            return FinancialSanityResult(status="FAIL", errors=["gross margin revenue denominator is zero"])
        expected = normalized_profit / normalized_revenue
        return _result(expected, float(declared_margin), "gross margin", rel_tol=1e-5, abs_tol=1e-7)

    def check_yoy(self, *, current: float, previous: float, declared_growth: float) -> FinancialSanityResult:
        if previous == 0:
            return FinancialSanityResult(status="FAIL", errors=["YoY previous-period denominator is zero"])
        expected = float(current) / float(previous) - 1.0
        return _result(expected, float(declared_growth), "YoY growth", rel_tol=1e-6, abs_tol=1e-9)

    def check_market_cap(
        self,
        *,
        shares_outstanding: float,
        price: float,
        declared_market_cap: float,
        declared_unit: str = "元",
    ) -> FinancialSanityResult:
        expected = float(shares_outstanding) * float(price)
        actual = normalize_to_yuan(declared_market_cap, declared_unit)
        return _result(expected, actual, "market cap")

    def check_target_price(
        self,
        *,
        scenario_market_cap: float,
        scenario_market_cap_unit: str,
        shares_outstanding: float,
        declared_target_price: float,
    ) -> FinancialSanityResult:
        if shares_outstanding == 0:
            return FinancialSanityResult(status="FAIL", errors=["target-price share denominator is zero"])
        expected = normalize_to_yuan(scenario_market_cap, scenario_market_cap_unit) / float(shares_outstanding)
        return _result(expected, float(declared_target_price), "target price")

    def check_consistency(self, observations: list[FinancialMetricObservation]) -> FinancialSanityResult:
        grouped: dict[tuple[str, str, str, str], list[FinancialMetricObservation]] = {}
        normalized: dict[str, float] = {}
        for item in observations:
            key = (item.metric, item.period, item.scope, item.version)
            grouped.setdefault(key, []).append(item)
            normalized["|".join(key)] = item.normalized_value

        errors: list[str] = []
        for key, items in grouped.items():
            if len(items) < 2:
                continue
            baseline = items[0].normalized_value
            for other in items[1:]:
                value = other.normalized_value
                if _matches(baseline, value):
                    continue
                magnitude = None
                if baseline != 0 and value != 0:
                    magnitude = max(abs(baseline), abs(value)) / min(abs(baseline), abs(value))
                if magnitude is not None and any(math.isclose(magnitude, x, rel_tol=1e-6) for x in (10, 100, 10_000)):
                    errors.append(f"scale conflict for {key}: values differ by approximately x{magnitude:g}")
                else:
                    errors.append(f"conflict for {key}: {baseline} vs {value}")
        return FinancialSanityResult(status="FAIL" if errors else "PASS", errors=errors, normalized_metrics=normalized)
