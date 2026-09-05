from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from research_os.policies import (
    PolicyDefinition,
    PolicyOverride,
    PolicyParameter,
    PolicyRegistry,
    PolicyRegistryConflictError,
    builtin_policy_definitions,
    builtin_policy_registry,
)
from research_os.capital.engine import CapitalEfficiencyEngine
from research_os.expectations.models import ConsensusVintage
from research_os.expectations.validation import ExpectationEvidenceValidator


def _policy(policy_id: str = "policy:test") -> PolicyDefinition:
    return PolicyDefinition(
        policy_id=policy_id,
        policy_version="1.0.0",
        policy_type="thresholds",
        applicability=frozenset({"research"}),
        parameters={
            "minimum_score": PolicyParameter(
                value=Decimal("0.4"),
                value_type="decimal",
                unit="ratio",
                minimum=Decimal("0"),
                maximum=Decimal("1"),
            )
        },
        rationale="Synthetic policy for registry behavior",
        source="research_os",
    )


def test_policy_registry_requires_unique_policy_id_and_version() -> None:
    with pytest.raises(PolicyRegistryConflictError, match="policy:test"):
        PolicyRegistry((_policy(), _policy()))
    with pytest.raises(PolicyRegistryConflictError, match="policy:test"):
        PolicyRegistry((_policy(), _policy().model_copy(update={"policy_version": "2.0.0"})))


def test_policy_parameter_enforces_declared_type_unit_and_range() -> None:
    with pytest.raises(ValidationError, match="declared decimal"):
        PolicyParameter(value="0.4", value_type="decimal", unit="ratio")
    with pytest.raises(ValidationError, match="unit"):
        PolicyParameter(value=Decimal("0.4"), value_type="decimal", unit="")
    with pytest.raises(ValidationError, match="maximum"):
        PolicyParameter(
            value=Decimal("1.1"),
            value_type="decimal",
            unit="ratio",
            minimum=Decimal("0"),
            maximum=Decimal("1"),
        )


def test_override_requires_operator_reason_time_and_matching_base_policy() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        PolicyOverride(
            policy_id="policy:test",
            base_policy_version="1.0.0",
            operator="analyst:1",
            reason="scenario-specific evidence",
            override_ts=datetime(2026, 9, 3, 9),
            parameters={
                "minimum_score": PolicyParameter(
                    value=Decimal("0.5"),
                    value_type="decimal",
                    unit="ratio",
                )
            },
        )

    override = PolicyOverride(
        policy_id="policy:test",
        base_policy_version="0.9.0",
        operator="analyst:1",
        reason="scenario-specific evidence",
        override_ts=datetime(2026, 9, 3, 9, tzinfo=timezone.utc),
        parameters={
            "minimum_score": PolicyParameter(
                value=Decimal("0.5"),
                value_type="decimal",
                unit="ratio",
            )
        },
    )
    with pytest.raises(ValueError, match="base policy"):
        PolicyRegistry((_policy(),), overrides=(override,))


def test_builtin_registry_contains_every_conclusion_policy_and_builds_snapshot() -> None:
    expected = {
        "business_model_routing",
        "expectation_quality",
        "funding_loop",
        "thesis_formation",
        "temporal_analysis",
        "valuation_fitness",
        "decision_aggregation",
        "forecast_promotion",
    }
    definitions = builtin_policy_definitions()
    registry = builtin_policy_registry()

    assert {item.policy_id for item in definitions} == expected
    assert {item.policy_id for item in registry.definitions} == expected
    assert {item.policy_id for item in registry.snapshot().policies} == expected


def test_temporal_policy_exposes_typed_comparison_thresholds() -> None:
    registry = builtin_policy_registry()

    assert registry.integer_value("temporal_analysis", "minimum_comparable_points") == 2
    assert registry.decimal_value("temporal_analysis", "stable_relative_change") == Decimal("0.01")
    assert registry.decimal_value("temporal_analysis", "anomaly_relative_change") == Decimal("0.30")


def test_expectation_and_funding_thresholds_use_actual_policy_overrides() -> None:
    override_ts = datetime(2026, 9, 3, tzinfo=timezone.utc)
    registry = PolicyRegistry(
        builtin_policy_definitions(),
        overrides=(
            PolicyOverride(
                policy_id="expectation_quality",
                base_policy_version="1.0.0",
                operator="analyst:1",
                reason="require stronger consensus sources",
                override_ts=override_ts,
                parameters={
                    "minimum_source_quality": _policy()
                    .parameters["minimum_score"]
                    .model_copy(update={"value": Decimal("0.8")})
                },
            ),
            PolicyOverride(
                policy_id="funding_loop",
                base_policy_version="1.0.0",
                operator="analyst:1",
                reason="company-specific factoring materiality",
                override_ts=override_ts,
                parameters={
                    "factoring_to_ar_materiality": _policy()
                    .parameters["minimum_score"]
                    .model_copy(update={"value": Decimal("0.5")})
                },
            ),
        ),
    )
    vintage = ConsensusVintage(
        company_id="synthetic:policy",
        vintage="2026-09-01",
        as_of=datetime(2026, 9, 1, tzinfo=timezone.utc),
        forecast_period="2026FY",
        estimates={},
        source_count=5,
        source_quality=0.6,
    )

    quality = ExpectationEvidenceValidator(policy_registry=registry).assess_consensus_quality(
        vintage=vintage,
        decision_ts=override_ts,
    )
    funding = CapitalEfficiencyEngine(policy_registry=registry).funding_loop(
        {"factoring_balance": 30, "ar": 100}
    )

    assert quality.status == "LOW"
    assert "LOW_SOURCE_QUALITY" in quality.reason_codes
    assert "MATERIAL_FACTORING_EXPOSURE" not in funding.reason_codes


def test_policy_definition_is_json_serializable() -> None:
    definition = builtin_policy_registry().require("forecast_promotion")

    payload = definition.model_dump(mode="json")

    assert payload["parameters"]["require_pit_compliance"]["value"] is True
