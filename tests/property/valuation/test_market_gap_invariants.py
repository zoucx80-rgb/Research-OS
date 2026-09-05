from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from hypothesis import given, strategies as st

from research_os.contracts.artifact_values import ValuationRange, ValuationReconciliation
from research_os.contracts.evidence import EvidenceRef
from research_os.valuation.market import PitMarketAnchor, ValuationMarketGapService


REFERENCE = EvidenceRef(
    evidence_id="ev:valuation:property",
    revision=1,
    content_fingerprint="a" * 64,
)
TIMESTAMP = datetime(2026, 8, 28, tzinfo=timezone.utc)
MONEY = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("10000"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


def _anchor(price: Decimal) -> PitMarketAnchor:
    return PitMarketAnchor(
        company_id="property:company",
        security_id="property:security",
        share_class="A",
        source_id="exchange:close",
        observed_ts=TIMESTAMP,
        available_ts=TIMESTAMP,
        price=price,
        currency="CNY",
        unit="CNY/share",
        valuation_basis="per_share",
        corporate_action_basis="unadjusted_close",
        evidence_refs=(REFERENCE,),
    )


def _ranges(low: Decimal, high: Decimal) -> tuple[ValuationRange, ...]:
    return tuple(
        ValuationRange(
            range_key=f"range:{index}",
            low=low,
            high=high,
            basis="per_share",
            currency="CNY",
            unit="CNY/share",
            share_class="A",
            corporate_action_basis="unadjusted_close",
            role="model_implied",
            evidence_refs=(REFERENCE,),
        )
        for index in (1, 2)
    )


@given(low=MONEY, width=MONEY, price=MONEY)
def test_market_gap_arithmetic_and_state_are_consistent(
    low: Decimal,
    width: Decimal,
    price: Decimal,
) -> None:
    high = low + width
    reconciliation = ValuationReconciliation(
        domain_status="SUPPORTED",
        reconciliation_status="INTERSECTION",
        method="mathematical_intersection",
        low=low,
        high=high,
        included_range_keys=("range:1", "range:2"),
        evidence_refs=(REFERENCE,),
    )

    gap = ValuationMarketGapService().compare(
        reconciliation,
        _ranges(low, high),
        _anchor(price),
    )

    assert gap.gap_low == low - price
    assert gap.gap_high == high - price
    if price < low:
        assert gap.state == "UNDERVALUED"
    elif price > high:
        assert gap.state == "OVERVALUED"
    else:
        assert gap.state == "FAIR"
