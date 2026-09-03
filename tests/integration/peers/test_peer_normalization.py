from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import Money
from research_os.peers.models import (
    ComparableAdjustment,
    ComparableMetric,
    ComparisonBasis,
)
from research_os.peers.normalization import PeerNormalizationError, normalize_peer_metric


def _ref(name: str) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=name,
        revision=1,
        content_fingerprint="c" * 64,
    )


def _basis(currency: str) -> ComparisonBasis:
    return ComparisonBasis(
        currency=currency,
        fiscal_year_end=date(2025, 12, 31),
        accounting_standard="IFRS",
        scope="consolidated",
        lease_treatment="capitalized",
        one_off_treatment="excluded",
        share_count_convention="diluted_weighted_average",
        valuation_date=date(2026, 1, 31),
    )


def _metric(peer_id: str, currency: str, amount: str) -> ComparableMetric:
    return ComparableMetric(
        peer_company_id=peer_id,
        metric_id="enterprise_value",
        value=Money(amount=Decimal(amount), currency=currency),
        basis=_basis(currency),
        evidence_refs=(_ref(f"source:{peer_id}"),),
    )


def test_normalization_refuses_to_guess_currency_adjustment() -> None:
    with pytest.raises(PeerNormalizationError, match="explicit adjustments"):
        normalize_peer_metric(_metric("left", "USD", "100"), _metric("right", "EUR", "90"))


def test_explicit_sourced_adjustment_produces_normalized_comparable() -> None:
    left = _metric("left", "USD", "100")
    right = _metric("right", "EUR", "90")
    adjustment = ComparableAdjustment(
        reason_code="CURRENCY_MISMATCH",
        method="Apply the supplied point-in-time EUR/USD rate.",
        normalized_left_value=Money(amount=Decimal("100"), currency="USD"),
        normalized_right_value=Money(amount=Decimal("99"), currency="USD"),
        operator="analyst@example.test",
        evidence_refs=(_ref("fx:2026-01-31"),),
    )

    normalized = normalize_peer_metric(
        left,
        right,
        adjustments=(adjustment,),
        target_basis=_basis("USD"),
    )

    assert normalized.status == "COMPARABLE"
    assert normalized.left_value.currency == "USD"
    assert normalized.right_value.currency == "USD"
    assert normalized.adjustments == (adjustment,)
    assert {item.evidence_id for item in normalized.evidence_refs} == {
        "source:left",
        "source:right",
        "fx:2026-01-31",
    }
