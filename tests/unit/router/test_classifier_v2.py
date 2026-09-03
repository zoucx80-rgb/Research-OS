from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from research_os.domain.evidence import Evidence
from research_os.policies import (
    PolicyOverride,
    PolicyParameter,
    PolicyRegistry,
    builtin_policy_definitions,
)
from research_os.router.classifier import BusinessModelRouter
from research_os.router.models import BusinessModelProfile


def _evidence(metric: str, value: object, *, period: str | None = None) -> Evidence:
    return Evidence(
        evidence_id=f"ev:{metric}",
        company_id="synthetic:router-v2",
        evidence_type="filing_fact",
        period=period,
        publish_ts=datetime(2026, 9, 1, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        value=value,
        source_table=metric,
        confidence_grade="A",
        verification_status="PRIMARY_VERIFIED",
    )


def test_router_separates_rule_score_coverage_counter_evidence_and_confidence() -> None:
    profile = BusinessModelRouter().classify(
        "synthetic:router-v2",
        (
            _evidence("business_description", "manufacturing and distribution"),
            _evidence("fixed_asset_to_assets", 0.30),
            _evidence("gross_margin", 0.18),
            _evidence("inventory_to_revenue", 0.35, period="FY2025"),
        ),
    )

    assert profile.classification_status == "CLASSIFIED"
    assert profile.primary_model == "manufacturing"
    assert profile.rule_match_score > 0
    assert 0 < profile.usable_evidence_coverage <= 1
    assert profile.confidence_band in {"LOW", "MEDIUM", "HIGH"}
    assert profile.ambiguity >= 0
    assert profile.positive_evidence
    assert profile.counter_evidence
    assert "probability" not in BusinessModelProfile.model_fields


def test_router_returns_unresolved_when_top_candidate_gap_is_below_policy() -> None:
    profile = BusinessModelRouter().classify(
        "synthetic:router-v2",
        (_evidence("business_description", "manufacturing distributor"),),
    )

    assert profile.classification_status == "UNRESOLVED"
    assert profile.primary_model == "unknown"
    assert profile.classification_reason == "CANDIDATE_GAP_BELOW_POLICY"
    assert {item.model_id for item in profile.candidates[:2]} == {
        "distributor",
        "manufacturing",
    }


def test_router_candidate_gap_threshold_comes_from_policy_override() -> None:
    override = PolicyOverride(
        policy_id="business_model_routing",
        base_policy_version="1.0.0",
        operator="analyst:router",
        reason="approved deterministic tie handling fixture",
        override_ts=datetime(2026, 9, 1, tzinfo=timezone.utc),
        parameters={
            "minimum_candidate_gap": PolicyParameter(
                value=Decimal("0"),
                value_type="decimal",
                unit="ratio",
                minimum=Decimal("0"),
                maximum=Decimal("1"),
            )
        },
    )
    policy = PolicyRegistry(builtin_policy_definitions(), overrides=(override,))

    profile = BusinessModelRouter(policy_registry=policy).classify(
        "synthetic:router-v2",
        (_evidence("business_description", "manufacturing distributor"),),
    )

    assert profile.classification_status == "CLASSIFIED"
    assert profile.primary_model == "distributor"
