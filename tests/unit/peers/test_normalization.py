from datetime import date
from decimal import Decimal

import pytest

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import Ratio
from research_os.peers.models import ComparableMetric, ComparisonBasis
from research_os.peers.normalization import PeerNormalizationError, normalize_peer_metric


def _metric(peer_id: str, fiscal_year_end: date) -> ComparableMetric:
    return ComparableMetric(
        peer_company_id=peer_id,
        metric_id="return_on_equity",
        value=Ratio(value=Decimal("0.1")),
        basis=ComparisonBasis(
            currency="USD",
            fiscal_year_end=fiscal_year_end,
            accounting_standard="US_GAAP",
            scope="consolidated",
            lease_treatment="capitalized",
            one_off_treatment="excluded",
            share_count_convention="diluted_weighted_average",
            valuation_date=date(2026, 1, 31),
        ),
        evidence_refs=(
            EvidenceRef(
                evidence_id=f"peer:{peer_id}",
                revision=1,
                content_fingerprint="d" * 64,
            ),
        ),
    )


def test_peer_comparison_rejects_different_fiscal_year_without_adjustment() -> None:
    with pytest.raises(PeerNormalizationError):
        normalize_peer_metric(
            _metric("left", date(2025, 6, 30)),
            _metric("right", date(2025, 12, 31)),
        )
