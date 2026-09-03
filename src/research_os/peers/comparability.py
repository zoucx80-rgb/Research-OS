from __future__ import annotations

from research_os.contracts.evidence import EvidenceRef
from research_os.peers.models import (
    ComparableMetric,
    ComparabilityAssessment,
    ComparabilityReasonCode,
)


_BASIS_REASON_CODES: tuple[tuple[str, ComparabilityReasonCode], ...] = (
    ("currency", "CURRENCY_MISMATCH"),
    ("fiscal_year_end", "FISCAL_YEAR_MISMATCH"),
    ("accounting_standard", "ACCOUNTING_STANDARD_MISMATCH"),
    ("scope", "SCOPE_MISMATCH"),
    ("lease_treatment", "LEASE_TREATMENT_MISMATCH"),
    ("one_off_treatment", "ONE_OFF_TREATMENT_MISMATCH"),
    ("share_count_convention", "SHARE_COUNT_MISMATCH"),
    ("valuation_date", "VALUATION_DATE_MISMATCH"),
)


def _unique_refs(*metrics: ComparableMetric) -> tuple[EvidenceRef, ...]:
    return tuple(
        {
            (item.evidence_id, item.revision, item.content_fingerprint): item
            for metric in metrics
            for item in metric.evidence_refs
        }.values()
    )


def assess_comparability(
    left: ComparableMetric, right: ComparableMetric
) -> ComparabilityAssessment:
    references = _unique_refs(left, right)
    if left.metric_id != right.metric_id:
        return ComparabilityAssessment(
            status="NOT_COMPARABLE",
            reason_codes=("METRIC_ID_MISMATCH",),
            evidence_refs=references,
        )
    if type(left.value) is not type(right.value):
        return ComparabilityAssessment(
            status="NOT_COMPARABLE",
            reason_codes=("VALUE_TYPE_MISMATCH",),
            evidence_refs=references,
        )
    if not left.basis.complete or not right.basis.complete:
        return ComparabilityAssessment(
            status="INSUFFICIENT_EVIDENCE",
            reason_codes=("MISSING_BASIS_EVIDENCE",),
            evidence_refs=references,
        )
    mismatches = tuple(
        reason
        for field, reason in _BASIS_REASON_CODES
        if getattr(left.basis, field) != getattr(right.basis, field)
    )
    return ComparabilityAssessment(
        status="ADJUSTMENT_REQUIRED" if mismatches else "COMPARABLE",
        reason_codes=mismatches,
        evidence_refs=references,
    )


__all__ = ["assess_comparability"]
