from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from research_os.contracts.artifact_values import ValuationExecution, ValuationResult
from research_os.contracts.evidence import EvidenceRef
from research_os.reporting.projectors import project_artifact
from research_os.valuation.market import PitMarketAnchor, ValuationMarketGap


REFERENCE = EvidenceRef(
    evidence_id="ev:valuation:report",
    revision=1,
    content_fingerprint="a" * 64,
)
OBSERVED_TS = datetime(2026, 8, 28, 7, 0, tzinfo=timezone.utc)


def test_market_gap_projector_displays_observation_time_and_basis() -> None:
    gap = ValuationMarketGap(
        domain_status="SUPPORTED",
        reconciliation_key="INTERSECTION:mathematical_intersection",
        market_anchor_security_id="300034.SZ",
        market_anchor_observed_ts=OBSERVED_TS,
        market_value=Decimal("12"),
        model_low=Decimal("18"),
        model_high=Decimal("22"),
        gap_low=Decimal("6"),
        gap_high=Decimal("10"),
        currency="CNY",
        valuation_basis="per_share",
        state="UNDERVALUED",
        comparison_status="PASS",
        evidence_refs=(REFERENCE,),
    )

    payload = project_artifact("valuation.market_gap", gap).payload

    assert payload["市场比较状态"] == "通过"
    assert payload["市场估值状态"] == "低估"
    assert payload["市场观测时点"] == "2026-08-28T07:00:00Z"
    assert payload["估值口径"] == "每股价值"
    assert payload["模型区间下限"] != "—"
    assert payload["相对市场差额下限"] != "—"


def test_market_anchor_and_controlled_execution_are_investor_readable() -> None:
    anchor = PitMarketAnchor(
        company_id="300034.SZ",
        security_id="300034.SZ",
        share_class="A",
        source_id="exchange:daily-close",
        observed_ts=OBSERVED_TS,
        available_ts=datetime(2026, 8, 28, 8, 0, tzinfo=timezone.utc),
        price=Decimal("12"),
        currency="CNY",
        unit="CNY/share",
        valuation_basis="per_share",
        corporate_action_basis="unadjusted_close",
        evidence_refs=(REFERENCE,),
    )
    execution = ValuationExecution(
        domain_status="SUPPORTED",
        execution_source="CONTROLLED",
        validation_status="PASS",
        selected_model="pe",
        results=(
            ValuationResult(
                model_key="pe",
                status="SUPPORTED",
                formula_version="pe@1.0.0",
                value=Decimal("20"),
                unit="CNY/share",
                evidence_refs=(REFERENCE,),
            ),
        ),
        evidence_refs=(REFERENCE,),
    )

    anchor_payload = project_artifact("valuation.market_anchor", anchor).payload
    execution_payload = project_artifact("valuation.execution", execution).payload
    assert anchor_payload["证券"] == "300034.SZ"
    assert anchor_payload["价格"] != "—"
    assert anchor_payload["复权口径"] == "未复权收盘价"
    assert execution_payload["执行来源"] == "受控执行"
    assert execution_payload["验证状态"] == "通过"
