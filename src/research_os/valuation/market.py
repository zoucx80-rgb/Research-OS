from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from research_os.contracts.artifact_values import (
    AssumptionRef,
    DomainArtifact,
    LineageValue,
    ValuationRange,
    ValuationReconciliation,
)
from research_os.contracts.evidence import EvidenceRef


class PitMarketAnchor(LineageValue):
    company_id: str
    security_id: str
    share_class: str
    source_id: str
    observed_ts: datetime
    available_ts: datetime
    price: Decimal = Field(gt=0)
    currency: str
    unit: str
    valuation_basis: Literal["per_share", "total_value"]
    corporate_action_basis: str

    @field_validator(
        "company_id",
        "security_id",
        "share_class",
        "source_id",
        "currency",
        "unit",
        "corporate_action_basis",
    )
    @classmethod
    def _non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("market anchor identity and basis fields must be non-empty")
        return normalized.upper() if len(normalized) == 3 else normalized

    @field_validator("observed_ts", "available_ts")
    @classmethod
    def _utc(cls, value: datetime, info: object) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{getattr(info, 'field_name', 'timestamp')} must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _pit_and_lineage(self) -> Self:
        if self.observed_ts > self.available_ts:
            raise ValueError("market anchor requires observed_ts <= available_ts")
        if not self.evidence_refs:
            raise ValueError("market anchor requires revision-bound evidence lineage")
        if self.valuation_basis == "per_share" and "/share" not in self.unit.lower():
            raise ValueError("per-share market anchor requires a per-share unit")
        if self.valuation_basis == "total_value" and "/share" in self.unit.lower():
            raise ValueError("total-value market anchor cannot use a per-share unit")
        return self


class ValuationMarketGap(DomainArtifact):
    reconciliation_key: str | None = None
    market_anchor_security_id: str | None = None
    market_anchor_observed_ts: datetime | None = None
    market_value: Decimal | None = None
    model_low: Decimal | None = None
    model_high: Decimal | None = None
    gap_low: Decimal | None = None
    gap_high: Decimal | None = None
    currency: str | None = None
    valuation_basis: str | None = None
    state: Literal["UNDERVALUED", "FAIR", "OVERVALUED", "UNKNOWN"] = "UNKNOWN"
    comparison_status: Literal[
        "PASS", "NOT_COMPARABLE", "INSUFFICIENT_EVIDENCE"
    ] = "INSUFFICIENT_EVIDENCE"
    reason_codes: tuple[str, ...] = ()

    @field_validator("reason_codes")
    @classmethod
    def _canonical_reasons(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("valuation market-gap reason codes must be non-empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("valuation market-gap reason codes must be unique")
        return tuple(sorted(normalized))

    @model_validator(mode="after")
    def _status_is_consistent(self) -> Self:
        values = (self.market_value, self.model_low, self.model_high, self.gap_low, self.gap_high)
        if self.comparison_status == "PASS":
            if self.domain_status != "SUPPORTED" or any(value is None for value in values):
                raise ValueError("passing market comparison requires supported numeric values")
            if self.state == "UNKNOWN" or self.reason_codes:
                raise ValueError("passing market comparison requires a known state without reasons")
        elif not self.reason_codes:
            raise ValueError("non-passing market comparison requires reason codes")
        return self


class MarketAnchorValidator:
    def validate(
        self,
        anchor: PitMarketAnchor,
        *,
        company_id: str,
        decision_ts: datetime,
    ) -> PitMarketAnchor:
        if decision_ts.tzinfo is None or decision_ts.utcoffset() is None:
            raise ValueError("decision_ts must be timezone-aware")
        decision_ts = decision_ts.astimezone(timezone.utc)
        if anchor.company_id != company_id:
            raise ValueError("market anchor company identity mismatch")
        if anchor.available_ts > decision_ts:
            raise ValueError("market anchor availability exceeds decision timestamp")
        return anchor


class ValuationMarketGapService:
    def compare(
        self,
        reconciliation: ValuationReconciliation,
        ranges: tuple[ValuationRange, ...],
        anchor: PitMarketAnchor | None,
    ) -> ValuationMarketGap:
        if anchor is None:
            return self._insufficient("MARKET_ANCHOR_MISSING")
        anchor_refs = anchor.evidence_refs
        if (
            reconciliation.domain_status != "SUPPORTED"
            or reconciliation.low is None
            or reconciliation.high is None
            or not reconciliation.included_range_keys
        ):
            return self._insufficient(
                "RECONCILIATION_NOT_BOUNDED",
                evidence_refs=anchor_refs,
                anchor=anchor,
            )
        by_key = {item.range_key: item for item in ranges}
        if len(by_key) != len(ranges):
            raise ValueError("valuation market-gap ranges must have unique identities")
        try:
            included = tuple(by_key[key] for key in reconciliation.included_range_keys)
        except KeyError:
            return self._insufficient(
                "VALUATION_RANGES_MISSING",
                evidence_refs=anchor_refs,
                anchor=anchor,
            )
        refs = self._evidence_refs((*included, anchor, reconciliation))
        assumptions = self._assumption_refs((*included, anchor, reconciliation))
        if any(item.role not in {"model_implied", "cross_check"} for item in included):
            return self._insufficient(
                "VALUATION_RANGE_ROLE_NOT_COMPARABLE",
                comparison_status="NOT_COMPARABLE",
                evidence_refs=refs,
                assumption_refs=assumptions,
                anchor=anchor,
            )
        if {item.basis for item in included} != {anchor.valuation_basis}:
            return self._insufficient(
                "VALUATION_BASIS_MISMATCH",
                comparison_status="NOT_COMPARABLE",
                evidence_refs=refs,
                assumption_refs=assumptions,
                anchor=anchor,
            )
        if {item.currency for item in included} != {anchor.currency}:
            return self._insufficient(
                "VALUATION_CURRENCY_MISMATCH",
                comparison_status="NOT_COMPARABLE",
                evidence_refs=refs,
                assumption_refs=assumptions,
                anchor=anchor,
            )
        if {item.unit for item in included} != {anchor.unit}:
            return self._insufficient(
                "VALUATION_UNIT_MISMATCH",
                comparison_status="NOT_COMPARABLE",
                evidence_refs=refs,
                assumption_refs=assumptions,
                anchor=anchor,
            )
        if {item.share_class for item in included} != {anchor.share_class}:
            return self._insufficient(
                "VALUATION_SHARE_CLASS_MISMATCH",
                comparison_status="NOT_COMPARABLE",
                evidence_refs=refs,
                assumption_refs=assumptions,
                anchor=anchor,
            )
        if {item.corporate_action_basis for item in included} != {
            anchor.corporate_action_basis
        }:
            return self._insufficient(
                "VALUATION_CORPORATE_ACTION_BASIS_MISMATCH",
                comparison_status="NOT_COMPARABLE",
                evidence_refs=refs,
                assumption_refs=assumptions,
                anchor=anchor,
            )
        low = Decimal(str(reconciliation.low))
        high = Decimal(str(reconciliation.high))
        price = anchor.price
        state: Literal["UNDERVALUED", "FAIR", "OVERVALUED"]
        if price < low:
            state = "UNDERVALUED"
        elif price > high:
            state = "OVERVALUED"
        else:
            state = "FAIR"
        return ValuationMarketGap(
            domain_status="SUPPORTED",
            reconciliation_key=(
                f"{reconciliation.reconciliation_status}:{reconciliation.method}"
            ),
            market_anchor_security_id=anchor.security_id,
            market_anchor_observed_ts=anchor.observed_ts,
            market_value=price,
            model_low=low,
            model_high=high,
            gap_low=low - price,
            gap_high=high - price,
            currency=anchor.currency,
            valuation_basis=anchor.valuation_basis,
            state=state,
            comparison_status="PASS",
            evidence_refs=refs,
            assumption_refs=assumptions,
        )

    @staticmethod
    def _insufficient(
        reason: str,
        *,
        comparison_status: Literal[
            "NOT_COMPARABLE", "INSUFFICIENT_EVIDENCE"
        ] = "INSUFFICIENT_EVIDENCE",
        evidence_refs: tuple[EvidenceRef, ...] = (),
        assumption_refs: tuple[AssumptionRef, ...] = (),
        anchor: PitMarketAnchor | None = None,
    ) -> ValuationMarketGap:
        return ValuationMarketGap(
            domain_status="INSUFFICIENT_EVIDENCE",
            market_anchor_security_id=None if anchor is None else anchor.security_id,
            market_anchor_observed_ts=None if anchor is None else anchor.observed_ts,
            market_value=None if anchor is None else anchor.price,
            currency=None if anchor is None else anchor.currency,
            valuation_basis=None if anchor is None else anchor.valuation_basis,
            comparison_status=comparison_status,
            reason_codes=(reason,),
            evidence_refs=evidence_refs,
            assumption_refs=assumption_refs,
        )

    @staticmethod
    def _evidence_refs(values: Iterable[LineageValue]) -> tuple[EvidenceRef, ...]:
        return tuple(
            {
                (ref.evidence_id, ref.revision, ref.content_fingerprint): ref
                for value in values
                for ref in value.evidence_refs
            }.values()
        )

    @staticmethod
    def _assumption_refs(values: Iterable[LineageValue]) -> tuple[AssumptionRef, ...]:
        return tuple(
            {
                (ref.assumption_key, ref.assumption_version, ref.content_fingerprint): ref
                for value in values
                for ref in value.assumption_refs
            }.values()
        )


__all__ = [
    "MarketAnchorValidator",
    "PitMarketAnchor",
    "ValuationMarketGap",
    "ValuationMarketGapService",
]
