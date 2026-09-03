from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import FinancialValue, Money


class PeerRole(StrEnum):
    DIRECT_COMPETITOR = "direct_competitor"
    BUSINESS_MODEL_PEER = "business_model_peer"
    SUPPLY_CHAIN_PEER = "supply_chain_peer"
    VALUATION_PEER = "valuation_peer"
    CAPITAL_EFFICIENCY_PEER = "capital_efficiency_peer"


ComparabilityStatus = Literal[
    "COMPARABLE",
    "ADJUSTMENT_REQUIRED",
    "NOT_COMPARABLE",
    "INSUFFICIENT_EVIDENCE",
]
ComparabilityReasonCode = Literal[
    "CURRENCY_MISMATCH",
    "FISCAL_YEAR_MISMATCH",
    "ACCOUNTING_STANDARD_MISMATCH",
    "SCOPE_MISMATCH",
    "LEASE_TREATMENT_MISMATCH",
    "ONE_OFF_TREATMENT_MISMATCH",
    "SHARE_COUNT_MISMATCH",
    "VALUATION_DATE_MISMATCH",
    "METRIC_ID_MISMATCH",
    "VALUE_TYPE_MISMATCH",
    "MISSING_BASIS_EVIDENCE",
]


class ComparisonBasis(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    currency: str | None
    fiscal_year_end: date | None
    accounting_standard: str | None
    scope: Literal["consolidated", "standalone"] | None
    lease_treatment: Literal["capitalized", "expensed"] | None
    one_off_treatment: Literal["included", "excluded"] | None
    share_count_convention: str | None
    valuation_date: date | None

    @field_validator("currency")
    @classmethod
    def _currency_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("comparison currency must be a three-letter code")
        return normalized

    @field_validator("accounting_standard", "share_count_convention")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("comparison basis text must be non-empty")
        return normalized

    @property
    def complete(self) -> bool:
        return all(
            value is not None
            for value in (
                self.currency,
                self.fiscal_year_end,
                self.accounting_standard,
                self.scope,
                self.lease_treatment,
                self.one_off_treatment,
                self.share_count_convention,
                self.valuation_date,
            )
        )


class ComparableMetric(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    peer_company_id: str
    metric_id: str
    value: FinancialValue
    basis: ComparisonBasis
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1)

    @field_validator("peer_company_id", "metric_id")
    @classmethod
    def _identity_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("comparable metric identity fields must be non-empty")
        return normalized

    @model_validator(mode="after")
    def _money_matches_declared_currency(self) -> ComparableMetric:
        if (
            isinstance(self.value, Money)
            and self.basis.currency is not None
            and self.value.currency != self.basis.currency
        ):
            raise ValueError("money currency must match comparison basis")
        return self


class ComparabilityAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: ComparabilityStatus
    reason_codes: tuple[ComparabilityReasonCode, ...]
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1)


class ComparableAdjustment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reason_code: ComparabilityReasonCode
    method: str
    normalized_left_value: FinancialValue
    normalized_right_value: FinancialValue
    operator: str
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1)

    @field_validator("method", "operator")
    @classmethod
    def _audit_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("peer adjustment audit fields must be non-empty")
        return normalized


class NormalizedComparable(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["COMPARABLE"] = "COMPARABLE"
    metric_id: str
    left_value: FinancialValue
    right_value: FinancialValue
    target_basis: ComparisonBasis
    adjustments: tuple[ComparableAdjustment, ...]
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1)


class PeerSelectionRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    peer_company_id: str
    role: PeerRole
    included: bool
    selection_reasons: tuple[str, ...] = ()
    exclusion_reasons: tuple[str, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _require_visible_selection_logic(self) -> PeerSelectionRecord:
        if self.included and not self.selection_reasons:
            raise ValueError("included peer requires a selection reason")
        if not self.included and not self.exclusion_reasons:
            raise ValueError("excluded peer requires an exclusion reason")
        return self


__all__ = [
    "ComparableAdjustment",
    "ComparableMetric",
    "ComparabilityAssessment",
    "ComparabilityReasonCode",
    "ComparabilityStatus",
    "ComparisonBasis",
    "NormalizedComparable",
    "PeerRole",
    "PeerSelectionRecord",
]
