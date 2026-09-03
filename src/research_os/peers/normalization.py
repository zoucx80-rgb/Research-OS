from __future__ import annotations

from collections.abc import Sequence

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import Money, Quantity, Ratio
from research_os.peers.comparability import assess_comparability
from research_os.peers.models import (
    ComparableAdjustment,
    ComparableMetric,
    ComparisonBasis,
    NormalizedComparable,
)


class PeerNormalizationError(ValueError):
    pass


def _unique_refs(
    left: ComparableMetric,
    right: ComparableMetric,
    adjustments: Sequence[ComparableAdjustment],
) -> tuple[EvidenceRef, ...]:
    return tuple(
        {
            (item.evidence_id, item.revision, item.content_fingerprint): item
            for item in (
                *left.evidence_refs,
                *right.evidence_refs,
                *(
                    reference
                    for adjustment in adjustments
                    for reference in adjustment.evidence_refs
                ),
            )
        }.values()
    )


def _validate_normalized_values(
    left: Money | Ratio | Quantity,
    right: Money | Ratio | Quantity,
    target_basis: ComparisonBasis,
) -> None:
    if type(left) is not type(right):
        raise PeerNormalizationError("normalized values must use the same value type")
    if isinstance(left, Money) and isinstance(right, Money):
        if (
            target_basis.currency is None
            or left.currency != target_basis.currency
            or right.currency != target_basis.currency
        ):
            raise PeerNormalizationError("normalized money values must match target-basis currency")
    if isinstance(left, Quantity) and isinstance(right, Quantity):
        if left.unit != right.unit:
            raise PeerNormalizationError("normalized quantities must use the same unit")


def normalize_peer_metric(
    left: ComparableMetric,
    right: ComparableMetric,
    *,
    adjustments: Sequence[ComparableAdjustment] = (),
    target_basis: ComparisonBasis | None = None,
) -> NormalizedComparable:
    assessment = assess_comparability(left, right)
    if assessment.status == "INSUFFICIENT_EVIDENCE":
        raise PeerNormalizationError("insufficient evidence for peer normalization")
    if assessment.status == "NOT_COMPARABLE":
        raise PeerNormalizationError("peer metrics are not comparable")
    if assessment.status == "COMPARABLE":
        if adjustments:
            raise PeerNormalizationError("no adjustments are required")
        _validate_normalized_values(left.value, right.value, left.basis)
        return NormalizedComparable(
            metric_id=left.metric_id,
            left_value=left.value,
            right_value=right.value,
            target_basis=left.basis,
            adjustments=(),
            evidence_refs=assessment.evidence_refs,
        )

    required = set(assessment.reason_codes)
    supplied = {adjustment.reason_code for adjustment in adjustments}
    if required != supplied or len(supplied) != len(tuple(adjustments)):
        raise PeerNormalizationError(
            "all basis mismatches require explicit adjustments with no duplicates"
        )
    if target_basis is None or not target_basis.complete:
        raise PeerNormalizationError("explicit adjustments require a complete target basis")
    latest = tuple(adjustments)[-1]
    _validate_normalized_values(
        latest.normalized_left_value,
        latest.normalized_right_value,
        target_basis,
    )
    return NormalizedComparable(
        metric_id=left.metric_id,
        left_value=latest.normalized_left_value,
        right_value=latest.normalized_right_value,
        target_basis=target_basis,
        adjustments=tuple(adjustments),
        evidence_refs=_unique_refs(left, right, adjustments),
    )


__all__ = [
    "ComparableMetric",
    "PeerNormalizationError",
    "normalize_peer_metric",
]
