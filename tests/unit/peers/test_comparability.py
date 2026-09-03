from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import Money, Ratio
from research_os.peers.comparability import assess_comparability
from research_os.peers.models import (
    ComparableMetric,
    ComparisonBasis,
    PeerSelectionRecord,
)


def _ref(name: str) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=name,
        revision=1,
        content_fingerprint="b" * 64,
    )


def _basis(**changes: object) -> ComparisonBasis:
    values: dict[str, object] = {
        "currency": "USD",
        "fiscal_year_end": date(2025, 12, 31),
        "accounting_standard": "US_GAAP",
        "scope": "consolidated",
        "lease_treatment": "capitalized",
        "one_off_treatment": "excluded",
        "share_count_convention": "diluted_weighted_average",
        "valuation_date": date(2026, 1, 31),
    }
    values.update(changes)
    return ComparisonBasis.model_validate(values)


def _metric(peer_id: str, basis: ComparisonBasis) -> ComparableMetric:
    return ComparableMetric(
        peer_company_id=peer_id,
        metric_id="enterprise_value",
        value=Money(amount=Decimal("100"), currency=basis.currency or "USD"),
        basis=basis,
        evidence_refs=(_ref(f"evidence:{peer_id}"),),
    )


@pytest.mark.parametrize(
    ("field", "value", "reason_code"),
    [
        ("currency", "EUR", "CURRENCY_MISMATCH"),
        ("fiscal_year_end", date(2025, 6, 30), "FISCAL_YEAR_MISMATCH"),
        ("accounting_standard", "IFRS", "ACCOUNTING_STANDARD_MISMATCH"),
        ("scope", "standalone", "SCOPE_MISMATCH"),
        ("lease_treatment", "expensed", "LEASE_TREATMENT_MISMATCH"),
        ("one_off_treatment", "included", "ONE_OFF_TREATMENT_MISMATCH"),
        ("share_count_convention", "period_end", "SHARE_COUNT_MISMATCH"),
        ("valuation_date", date(2026, 2, 28), "VALUATION_DATE_MISMATCH"),
    ],
)
def test_material_basis_mismatch_requires_explicit_adjustment(
    field: str, value: object, reason_code: str
) -> None:
    assessment = assess_comparability(
        _metric("left", _basis()),
        _metric("right", _basis(**{field: value})),
    )

    assert assessment.status == "ADJUSTMENT_REQUIRED"
    assert reason_code in assessment.reason_codes


def test_missing_basis_is_insufficient_and_different_metric_is_not_comparable() -> None:
    missing = assess_comparability(
        _metric("left", _basis()),
        _metric("right", _basis(accounting_standard=None)),
    )
    assert missing.status == "INSUFFICIENT_EVIDENCE"
    assert "MISSING_BASIS_EVIDENCE" in missing.reason_codes

    other = _metric("right", _basis()).model_copy(update={"metric_id": "revenue"})
    incompatible = assess_comparability(_metric("left", _basis()), other)
    assert incompatible.status == "NOT_COMPARABLE"
    assert "METRIC_ID_MISMATCH" in incompatible.reason_codes

    different_value_kind = _metric("right", _basis()).model_copy(
        update={"value": Ratio(value=Decimal("1"))}
    )
    incompatible_kind = assess_comparability(
        _metric("left", _basis()), different_value_kind
    )
    assert incompatible_kind.status == "NOT_COMPARABLE"
    assert "VALUE_TYPE_MISMATCH" in incompatible_kind.reason_codes


def test_peer_selection_and_exclusion_reasons_are_mandatory() -> None:
    selected = PeerSelectionRecord(
        peer_company_id="peer:selected",
        role="valuation_peer",
        included=True,
        selection_reasons=("Similar capital intensity and revenue model.",),
        evidence_refs=(_ref("selection"),),
    )
    assert selected.selection_reasons

    excluded = PeerSelectionRecord(
        peer_company_id="peer:excluded",
        role="valuation_peer",
        included=False,
        exclusion_reasons=("Accounting scope cannot be reconciled.",),
        evidence_refs=(_ref("exclusion"),),
    )
    assert excluded.exclusion_reasons

    with pytest.raises(ValidationError, match="selection reason"):
        PeerSelectionRecord(
            peer_company_id="peer:opaque",
            role="valuation_peer",
            included=True,
            evidence_refs=(_ref("opaque"),),
        )
