from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from research_os.contracts.artifact_values import ValuationRange, ValuationReconciliation
from research_os.contracts.evidence import EvidenceRef
from research_os.valuation.market import (
    PitMarketAnchor,
    ValuationMarketGapService,
)


DECISION_TS = datetime(2026, 8, 30, tzinfo=timezone.utc)


def _reference(identity: str) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=identity,
        revision=1,
        content_fingerprint=("a" if identity.endswith("anchor") else "b") * 64,
    )


def _anchor(**updates: object) -> PitMarketAnchor:
    payload = {
        "company_id": "300034.SZ",
        "security_id": "300034.SZ",
        "share_class": "A",
        "source_id": "szse:daily-close",
        "observed_ts": datetime(2026, 8, 28, 7, 0, tzinfo=timezone.utc),
        "available_ts": datetime(2026, 8, 28, 8, 0, tzinfo=timezone.utc),
        "price": Decimal("15"),
        "currency": "CNY",
        "unit": "CNY/share",
        "valuation_basis": "per_share",
        "corporate_action_basis": "unadjusted_close",
        "evidence_refs": (_reference("ev:market:anchor"),),
    }
    payload.update(updates)
    return PitMarketAnchor.model_validate(payload)


def _ranges(*, basis: str = "per_share", unit: str = "CNY/share") -> tuple[ValuationRange, ...]:
    return tuple(
        ValuationRange(
            range_key=f"range:{index}",
            low=low,
            high=high,
            basis=basis,
            currency="CNY",
            unit=unit,
            share_class="A",
            corporate_action_basis="unadjusted_close",
            role="model_implied",
            evidence_refs=(_reference(f"ev:range:{index}"),),
        )
        for index, low, high in ((1, Decimal("8"), Decimal("20")), (2, Decimal("10"), Decimal("22")))
    )


def _reconciliation() -> ValuationReconciliation:
    return ValuationReconciliation(
        domain_status="SUPPORTED",
        reconciliation_status="INTERSECTION",
        method="mathematical_intersection",
        low=Decimal("10"),
        high=Decimal("20"),
        included_range_keys=("range:1", "range:2"),
        evidence_refs=tuple(item for value in _ranges() for item in value.evidence_refs),
    )


def test_market_anchor_requires_pit_order() -> None:
    with pytest.raises(ValidationError, match="observed_ts <= available_ts"):
        _anchor(
            observed_ts=DECISION_TS,
            available_ts=DECISION_TS - timedelta(days=1),
        )


def test_incompatible_basis_is_not_compared() -> None:
    gap = ValuationMarketGapService().compare(
        _reconciliation(),
        _ranges(basis="total_value", unit="CNY"),
        _anchor(),
    )

    assert gap.domain_status == "INSUFFICIENT_EVIDENCE"
    assert gap.comparison_status == "NOT_COMPARABLE"
    assert gap.reason_codes == ("VALUATION_BASIS_MISMATCH",)


@pytest.mark.parametrize(
    ("price", "expected"),
    ((Decimal("9"), "UNDERVALUED"), (Decimal("15"), "FAIR"), (Decimal("21"), "OVERVALUED")),
)
def test_market_state_compares_price_with_model_band(
    price: Decimal,
    expected: str,
) -> None:
    gap = ValuationMarketGapService().compare(
        _reconciliation(),
        _ranges(),
        _anchor(price=price),
    )

    assert gap.domain_status == "SUPPORTED"
    assert gap.comparison_status == "PASS"
    assert gap.state == expected
    assert gap.gap_low == Decimal("10") - price
    assert gap.gap_high == Decimal("20") - price
