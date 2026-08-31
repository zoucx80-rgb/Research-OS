from __future__ import annotations

import math
import re
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ValuationRole = Literal["model_implied", "scenario", "market_anchor", "cross_check"]


class ValuationRange(BaseModel):
    model_config = ConfigDict(frozen=True)

    range_id: str
    model_id: str
    role: ValuationRole
    basis: str
    currency: str
    low: float
    high: float
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    assumption_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("range_id", "model_id", "basis", "currency")
    @classmethod
    def _nonempty_identity(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("valuation identifiers, basis and currency must not be blank")
        return text

    @field_validator("low", "high")
    @classmethod
    def _finite_bound(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("valuation range bounds must be finite")
        return value

    @model_validator(mode="after")
    def _ordered_bounds(self) -> Self:
        if self.low > self.high:
            raise ValueError("valuation range low must not exceed high")
        return self


class ValuationModelRationale(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_id: str
    status: Literal["PRIMARY", "SECONDARY", "DOWNGRADED", "NOT_APPLICABLE"]
    economic_factors: tuple[
        Literal[
            "cash_flow_visibility",
            "forecast_horizon",
            "capital_intensity",
            "terminal_value_sensitivity",
            "evidence_quality",
            "model_assumptions",
            "business_model_fit",
        ],
        ...,
    ] = Field(min_length=1)
    explanation: str
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    assumption_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("model_id")
    @classmethod
    def _nonempty_model_id(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("valuation rationale model_id must not be blank")
        return text

    @field_validator("explanation")
    @classmethod
    def _economic_reason_only(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("valuation rationale must not be empty")
        forbidden = re.compile(
            r"research\s*os|renderer|release\s+version|software\s+version|"
            r"v\d+\.\d+\.\d+|"
            r"\b(?:build|release|software|version)\b.{0,40}\b\d+\.\d+\.\d+\b|"
            r"\b\d+\.\d+\.\d+\b.{0,40}\b(?:build|release|software|version)\b|"
            r"(?:版本|构建|发布版|软件|渲染器).{0,40}v?\d+\.\d+\.\d+|"
            r"v?\d+\.\d+\.\d+.{0,40}(?:版本|构建|发布版|软件|渲染器)",
            re.IGNORECASE,
        )
        if forbidden.search(text):
            raise ValueError("software or release version is not an economic rationale")
        return text


class ValuationReconciliation(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal[
        "INTERSECTION",
        "CROSS_CHECK_BAND",
        "MODEL_DISAGREEMENT",
        "NOT_COMPARABLE",
        "INSUFFICIENT_EVIDENCE",
    ]
    method: Literal["mathematical_intersection", "cross_check_envelope", "none"]
    low: float | None = None
    high: float | None = None
    basis: str | None = None
    currency: str | None = None
    included_range_ids: tuple[str, ...] = Field(default_factory=tuple)
    excluded_range_ids: tuple[str, ...] = Field(default_factory=tuple)
    reason: str

    @field_validator("basis", "currency")
    @classmethod
    def _nonempty_optional_context(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("reconciliation basis and currency must not be blank")
        return text

    @field_validator("reason")
    @classmethod
    def _nonempty_reason(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("reconciliation reason must not be blank")
        return text

    @field_validator("included_range_ids", "excluded_range_ids")
    @classmethod
    def _unique_nonempty_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("reconciliation range ids must not be blank")
        if len(set(normalized)) != len(normalized):
            raise ValueError("reconciliation range ids must be unique")
        return normalized

    @model_validator(mode="after")
    def _consistent_result(self) -> Self:
        bounded_methods = {
            "INTERSECTION": "mathematical_intersection",
            "CROSS_CHECK_BAND": "cross_check_envelope",
        }
        expected_method = bounded_methods.get(self.status)
        if expected_method is not None:
            if self.method != expected_method:
                raise ValueError("reconciliation status and method are inconsistent")
            if None in (self.low, self.high, self.basis, self.currency):
                raise ValueError("bounded reconciliation requires bounds, basis and currency")
            if not self.included_range_ids:
                raise ValueError("bounded reconciliation requires included ranges")
        else:
            if self.method != "none":
                raise ValueError("unbounded reconciliation must use method none")
            if self.low is not None or self.high is not None:
                raise ValueError("unbounded reconciliation must not expose bounds")

        if self.low is not None and (
            not math.isfinite(self.low)
            or self.high is None
            or not math.isfinite(self.high)
            or self.low > self.high
        ):
            raise ValueError("reconciliation bounds must be finite and ordered")
        if set(self.included_range_ids) & set(self.excluded_range_ids):
            raise ValueError("a valuation range cannot be both included and excluded")
        if self.status in {
            "INTERSECTION",
            "CROSS_CHECK_BAND",
            "MODEL_DISAGREEMENT",
        } and len(self.included_range_ids) < 2:
            raise ValueError("reconciliation comparison requires at least two ranges")
        if self.status == "MODEL_DISAGREEMENT" and (
            self.basis is None or self.currency is None
        ):
            raise ValueError("model disagreement requires basis and currency")
        return self


class ValuationReconciler:
    @staticmethod
    def _compatible(ranges: tuple[ValuationRange, ...]) -> bool:
        return len({item.basis for item in ranges}) == 1 and len(
            {item.currency for item in ranges}
        ) == 1

    @staticmethod
    def _not_comparable(
        ranges: tuple[ValuationRange, ...], reason: str
    ) -> ValuationReconciliation:
        return ValuationReconciliation(
            status="NOT_COMPARABLE",
            method="none",
            excluded_range_ids=tuple(item.range_id for item in ranges),
            reason=reason,
        )
    @classmethod
    def reconcile(
        cls, ranges: tuple[ValuationRange, ...]
    ) -> ValuationReconciliation:
        range_ids = tuple(item.range_id for item in ranges)
        if len(set(range_ids)) != len(range_ids):
            raise ValueError("valuation range_id values must be unique")
        if len(ranges) < 2:
            return ValuationReconciliation(
                status="INSUFFICIENT_EVIDENCE",
                method="none",
                included_range_ids=tuple(item.range_id for item in ranges),
                reason="at least two ranges are required for reconciliation",
            )

        model_ranges = tuple(item for item in ranges if item.role == "model_implied")
        if len(model_ranges) >= 2:
            non_model = tuple(item for item in ranges if item.role != "model_implied")
            if not cls._compatible(model_ranges):
                return cls._not_comparable(
                    ranges,
                    "model-implied ranges use incompatible valuation bases or currencies",
                )
            low = max(item.low for item in model_ranges)
            high = min(item.high for item in model_ranges)
            if low > high:
                return ValuationReconciliation(
                    status="MODEL_DISAGREEMENT",
                    method="none",
                    basis=model_ranges[0].basis,
                    currency=model_ranges[0].currency,
                    included_range_ids=tuple(item.range_id for item in model_ranges),
                    excluded_range_ids=tuple(item.range_id for item in non_model),
                    reason="compatible model-implied ranges do not overlap",
                )
            return ValuationReconciliation(
                status="INTERSECTION",
                method="mathematical_intersection",
                low=low,
                high=high,
                basis=model_ranges[0].basis,
                currency=model_ranges[0].currency,
                included_range_ids=tuple(item.range_id for item in model_ranges),
                excluded_range_ids=tuple(item.range_id for item in non_model),
                reason="compatible model-implied ranges have a non-empty intersection",
            )

        if all(item.role == "cross_check" for item in ranges):
            if not cls._compatible(ranges):
                return cls._not_comparable(
                    ranges,
                    "cross-check ranges use incompatible valuation bases or currencies",
                )
            return ValuationReconciliation(
                status="CROSS_CHECK_BAND",
                method="cross_check_envelope",
                low=min(item.low for item in ranges),
                high=max(item.high for item in ranges),
                basis=ranges[0].basis,
                currency=ranges[0].currency,
                included_range_ids=tuple(item.range_id for item in ranges),
                reason="compatible cross-check ranges are shown as an envelope",
            )

        return cls._not_comparable(
            ranges,
            "scenario, market-anchor and model-implied roles cannot be mathematically combined",
        )
