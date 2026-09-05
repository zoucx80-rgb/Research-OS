from __future__ import annotations

from decimal import Decimal

from research_os.policies.models import PolicyDefinition, PolicyParameter
from research_os.policies.registry import PolicyRegistry


def _ratio(value: str) -> PolicyParameter:
    return PolicyParameter(
        value=Decimal(value),
        value_type="decimal",
        unit="ratio",
        minimum=Decimal("0"),
        maximum=Decimal("1"),
    )


def _count(value: int) -> PolicyParameter:
    return PolicyParameter(
        value=value,
        value_type="integer",
        unit="count",
        minimum=0,
    )


def _policy(
    policy_id: str,
    policy_type: str,
    parameters: dict[str, PolicyParameter],
    rationale: str,
    *,
    policy_version: str = "1.0.0",
) -> PolicyDefinition:
    return PolicyDefinition(
        policy_id=policy_id,
        policy_version=policy_version,
        policy_type=policy_type,
        applicability=frozenset({"core_api:2.0"}),
        parameters=parameters,
        rationale=rationale,
        source="research_os:1.6.0",
    )


def builtin_policy_definitions() -> tuple[PolicyDefinition, ...]:
    definitions = (
        _policy(
            "business_model_routing",
            "classification",
            {
                "lease_materiality": _ratio("0.20"),
                "inventory_to_revenue_distributor": _ratio("0.15"),
                "asset_light_maximum": _ratio("0.08"),
                "low_gross_margin_maximum": _ratio("0.10"),
                "asset_heavy_minimum": _ratio("0.20"),
                "manufacturing_margin_minimum": _ratio("0.15"),
                "minimum_candidate_gap": _ratio("0.10"),
                "secondary_score_minimum": _ratio("0.30"),
                "high_confidence_coverage": _ratio("0.75"),
                "medium_confidence_coverage": _ratio("0.45"),
                "description_general_weight": _ratio("0.50"),
                "description_specialized_weight": _ratio("0.70"),
                "inventory_signal_weight": _ratio("0.20"),
                "asset_light_signal_weight": _ratio("0.15"),
                "low_margin_signal_weight": _ratio("0.15"),
                "asset_heavy_signal_weight": _ratio("0.25"),
                "manufacturing_margin_weight": _ratio("0.15"),
            },
            "Separate rule score, evidence coverage, ambiguity and confidence bands.",
        ),
        _policy(
            "expectation_quality",
            "evidence_quality",
            {
                "minimum_source_count": _count(3),
                "minimum_source_quality": _ratio("0.50"),
                "maximum_consensus_age_days": PolicyParameter(
                    value=90,
                    value_type="integer",
                    unit="days",
                    minimum=0,
                ),
                "minimum_gap_source_count": _count(2),
                "high_quality_source": _ratio("0.70"),
            },
            "Fail closed when expectation vintages lack sufficiently reliable sources.",
        ),
        _policy(
            "funding_loop",
            "materiality",
            {
                "factoring_to_ar_materiality": _ratio("0.20"),
                "incremental_working_capital_high": _ratio("0.40"),
                "debt_share_high": _ratio("0.60"),
                "debt_share_stressed": PolicyParameter(
                    value=Decimal("1.20"),
                    value_type="decimal",
                    unit="ratio",
                    minimum=Decimal("0"),
                ),
            },
            "Identify material external-funding dependence without inventing missing inputs.",
        ),
        _policy(
            "thesis_formation",
            "classification",
            {
                "receivables_growth_spread": _ratio("0.10"),
                "high_receivables_growth": _ratio("0.30"),
                "high_inventory_growth": _ratio("0.30"),
                "funding_debt_share_falsifier": _ratio("0.60"),
                "minimum_positive_signals": _count(2),
                "minimum_primary_confidence": _ratio("0.60"),
                "minimum_primary_evidence": _count(1),
            },
            "Form theses from explicit support and falsification thresholds.",
        ),
        _policy(
            "temporal_analysis",
            "comparison",
            {
                "minimum_comparable_points": _count(2),
                "stable_relative_change": _ratio("0.01"),
                "anomaly_relative_change": _ratio("0.30"),
            },
            "Derive descriptive trends only from explicit comparable period evidence.",
        ),
        _policy(
            "valuation_fitness",
            "method_support",
            {
                "primary_relative_score": _ratio("0.85"),
                "primary_absolute_score": _ratio("0.18"),
                "secondary_relative_score": _ratio("0.55"),
                "secondary_absolute_score": _ratio("0.08"),
                "minimum_data_quality": _ratio("0.50"),
                "supported_factor_minimum": _ratio("0.60"),
                "sanity_check_factor_minimum": _ratio("0.30"),
                "contraindicated_factor_maximum": _ratio("0.25"),
            },
            "Select valuation methods using economic support states and explicit gates.",
        ),
        _policy(
            "decision_aggregation",
            "decision_state",
            {
                "minimum_evidence_confidence": _ratio("0.40"),
                "material_funding_risk_veto": PolicyParameter(
                    value=True,
                    value_type="boolean",
                    unit="flag",
                ),
            },
            "Aggregate every thesis and material risk before assigning a decision state.",
            policy_version="2.0.2",
        ),
        _policy(
            "forecast_promotion",
            "model_governance",
            {
                "minimum_benchmark_improvement": _ratio("0"),
                "minimum_out_of_sample_folds": _count(1),
                "require_pit_compliance": PolicyParameter(
                    value=True,
                    value_type="boolean",
                    unit="flag",
                ),
                "require_stability": PolicyParameter(
                    value=True,
                    value_type="boolean",
                    unit="flag",
                ),
            },
            "Promote only PIT-compliant models with registered benchmark evidence.",
        ),
    )
    return tuple(sorted(definitions, key=lambda item: item.policy_id))


def builtin_policy_registry() -> PolicyRegistry:
    return PolicyRegistry(builtin_policy_definitions())


__all__ = ["builtin_policy_definitions", "builtin_policy_registry"]
