from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from research_os.contracts.evidence import EvidenceRef
from research_os.domain.evidence import Evidence
from research_os.router.classifier import BusinessModelRouter
from research_os.router.models import BusinessModelProfile


def ev(metric, value, *, period=None):
    return Evidence(
        evidence_id=metric,
        company_id="001287.SZ",
        evidence_type="calculated_metric",
        period=period,
        publish_ts=datetime(2026, 8, 25, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
        value=value,
        source_table=metric,
        confidence_grade="B",
        verification_status="PRIMARY_VERIFIED",
    )


def test_router_classifies_high_inventory_low_fixed_asset_company_as_distributor():
    profile = BusinessModelRouter().classify(
        "001287.SZ",
        [
            ev("inventory_to_revenue", 0.28),
            ev("fixed_asset_to_assets", 0.01),
            ev("gross_margin", 0.03),
            ev("business_description", "electronic component distribution"),
        ],
    )
    assert profile.primary_model == "distributor"
    assert profile.rule_match_score >= 0.80
    assert all(isinstance(reference, EvidenceRef) for reference in profile.evidence_refs)
    assert {reference.evidence_id for reference in profile.evidence_refs} == {
        "fixed_asset_to_assets",
        "gross_margin",
        "business_description",
    }


def test_router_profile_keeps_only_evidence_used_by_classification():
    profile = BusinessModelRouter().classify(
        "001287.SZ",
        [
            ev("business_description", "precision manufacturing"),
            ev("unrelated_fact", 123),
        ],
    )

    assert tuple(reference.evidence_id for reference in profile.evidence_refs) == (
        "business_description",
    )


def test_business_model_profile_rejects_id_only_lineage():
    with pytest.raises(ValidationError, match="evidence_ids"):
        BusinessModelProfile.model_validate(
            {
                "company_id": "001287.SZ",
                "primary_model": "manufacturing",
                "confidence": 0.8,
                "evidence_ids": ["business_description"],
            }
        )


def test_router_recognizes_other_standard_business_models_from_primary_business_description():
    cases = {
        "subscription software SaaS cloud recurring revenue": "software",
        "consumer brand retail food beverage": "consumer",
        "copper mining resource commodity producer": "resource",
        "EPC engineering project system integration": "project",
        "commercial bank financial services deposits loans": "financial",
    }
    for desc, expected in cases.items():
        p = BusinessModelRouter().classify("X", [ev("business_description", desc)])
        assert p.primary_model == expected, (desc, p)


def test_interim_inventory_to_revenue_does_not_add_distributor_score():
    profile = BusinessModelRouter().classify(
        "X", [ev("inventory_to_revenue", 0.80, period="2026H1")]
    )

    assert profile.primary_model == "unknown"
    assert profile.classification_status == "INSUFFICIENT_EVIDENCE"


def test_annual_inventory_to_revenue_can_add_distributor_score():
    profile = BusinessModelRouter().classify(
        "X", [ev("inventory_to_revenue", 0.28, period="FY2025")]
    )

    assert profile.primary_model == "distributor"
    assert profile.classification_status == "CLASSIFIED"


def test_router_represents_hospitality_without_industry_plugin_assumption():
    profile = BusinessModelRouter().classify(
        "301073.SZ",
        [ev("business_description", "酒店运营与酒店管理 hospitality hotel")],
    )

    assert profile.primary_model == "hospitality"
    assert profile.classification_status == "CLASSIFIED"


def test_router_distinguishes_unsupported_taxonomy_from_missing_evidence():
    unsupported = BusinessModelRouter().classify(
        "X", [ev("business_description", "specialized laboratory testing services")]
    )
    missing = BusinessModelRouter().classify("Y", [])

    assert unsupported.primary_model == "unknown"
    assert unsupported.classification_status == "UNSUPPORTED_TAXONOMY"
    assert missing.primary_model == "unknown"
    assert missing.classification_status == "INSUFFICIENT_EVIDENCE"
