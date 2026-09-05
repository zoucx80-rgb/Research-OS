from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .baseline import CHECKS as _BASELINE_CHECKS
from .manifest import ReleaseManifest


@dataclass(frozen=True)
class VerificationPack:
    pack_id: str
    check_ids: tuple[str, ...]


_RELEASE_GOVERNANCE_CHECKS: dict[str, str] = {
    "release_governance": "tests/regression/architecture/test_release_governance.py",
}
_M2_PERSISTENCE_HTTP_CHECKS: dict[str, str] = {
    "snapshot_schema_v2": "tests/unit/snapshots",
    "snapshot_canonicalization_v2": "tests/property/snapshots",
    "sql_persistence_v2": "tests/integration/storage",
    "runtime_snapshot_transaction_v2": (
        "tests/integration/runtime/test_run_snapshot_transaction.py"
    ),
    "http_api_v1_unit": "tests/unit/api",
    "http_api_v1_integration": "tests/integration/api",
    "http_api_v1_contract": "tests/contract/api",
}
_M3_PROFESSIONAL_FOUNDATIONS_CHECKS: dict[str, str] = {
    "m3_financial_values": "tests/unit/contracts/test_financial_values.py",
    "m3_metrics": "tests/unit/metrics",
    "m3_policies": "tests/unit/policies",
    "m3_router": "tests/unit/router",
    "m3_thesis": "tests/unit/thesis",
    "m3_decision": "tests/unit/decision",
    "m3_thesis_decision": "tests/integration/runtime/test_portfolio_decision.py",
    "m3_valuation": "tests/unit/valuation",
    "m3_forecasting": "tests/unit/forecasting",
    "m3_peers": "tests/unit/peers",
    "m3_monitoring": "tests/unit/monitoring",
}
_M4_REPORTING_REPLAY_CHECKS: dict[str, str] = {
    "current_reporting_v2": "tests/unit/reporting/test_v1_6_current_reporting.py",
    "historical_replay_v2": "tests/unit/release/test_historical_replay_v1_6.py",
    "presentation_pipeline_v2": "tests/integration/presentation/test_v1_6_pipeline.py",
    "field_acceptance_contract_v2": (
        "tests/integration/presentation/test_field_acceptance_v1_6_0.py"
    ),
    "clean_break_v2": "tests/regression/architecture/test_clean_break_v1_6.py",
    "v1_6_examples": "tests/integration/examples/test_v1_6_examples.py",
}
_M5_QUALITY_RELEASE_CHECKS: dict[str, str] = {
    "m5_dependency_rules": "tests/regression/architecture/test_dependency_rules_v1_6.py",
    "m5_repository_hygiene": "tests/regression/architecture/test_repository_hygiene_v1_6.py",
    "m5_release_contract": "tests/regression/architecture/test_release_contract_v1_6_0.py",
    "m5_installed_distribution": "tests/integration/package/test_installed_distribution.py",
}
_V1_6_01_PROFESSIONAL_CLOSURE_CHECKS: dict[str, str] = {
    "v1_6_01_professional_wiring": (
        "tests/regression/professional/test_v1_6_01_professional_wiring.py"
    ),
    "v1_6_01_investor_body": ("tests/regression/presentation/test_v1_6_01_investor_body.py"),
    "v1_6_01_section_ids": "tests/integration/presentation/test_v1_6_01_section_ids.py",
    "v1_6_01_field_acceptance_contract": (
        "tests/integration/presentation/test_field_acceptance_v1_6_01.py"
    ),
}
_V1_6_02_TEMPORAL_CHECKS: dict[str, str] = {
    "v1_6_02_temporal_unit": "tests/unit/temporal",
    "v1_6_02_temporal_property": "tests/property/temporal",
    "v1_6_02_sufficiency_unit": "tests/unit/sufficiency",
    "v1_6_02_temporal_runtime": "tests/integration/runtime/test_temporal_sufficiency.py",
    "v1_6_02_temporal_field": (
        "tests/regression/professional/test_v1_6_02_temporal_sufficiency.py"
    ),
}
_V1_6_02_FORECAST_CHECKS: dict[str, str] = {
    "v1_6_02_forecast_unit": "tests/unit/forecasting",
    "v1_6_02_forecast_integration": "tests/integration/forecasting",
    "v1_6_02_forecast_runtime": (
        "tests/integration/runtime/test_professional_forecast_benchmark.py"
    ),
    "v1_6_02_forecast_field": (
        "tests/regression/professional/test_v1_6_02_forecast_benchmark.py"
    ),
}
_V1_6_02_VALUATION_CHECKS: dict[str, str] = {
    "v1_6_02_valuation_unit": "tests/unit/valuation",
    "v1_6_02_valuation_property": "tests/property/valuation",
    "v1_6_02_valuation_runtime": (
        "tests/integration/runtime/test_valuation_market_gap.py"
    ),
    "v1_6_02_valuation_field": (
        "tests/regression/professional/test_v1_6_02_valuation_market_gap.py"
    ),
    "v1_6_02_valuation_reporting": (
        "tests/unit/reporting/test_v1_6_02_valuation.py"
    ),
}
_V1_6_02_DECISION_CHECKS: dict[str, str] = {
    "v1_6_02_decision_unit": "tests/unit/decision",
    "v1_6_02_decision_property": "tests/property/decision",
    "v1_6_02_decision_runtime": (
        "tests/integration/runtime/test_decision_context_v1_6_02.py"
    ),
    "v1_6_02_decision_field": (
        "tests/regression/professional/test_v1_6_02_decision_context.py"
    ),
    "v1_6_02_decision_reporting": (
        "tests/unit/reporting/test_v1_6_02_decision.py"
    ),
}

CHECK_REGISTRY: Mapping[str, str] = {
    **_BASELINE_CHECKS,
    **_M2_PERSISTENCE_HTTP_CHECKS,
    **_M3_PROFESSIONAL_FOUNDATIONS_CHECKS,
    **_M4_REPORTING_REPLAY_CHECKS,
    **_M5_QUALITY_RELEASE_CHECKS,
    **_V1_6_01_PROFESSIONAL_CLOSURE_CHECKS,
    **_V1_6_02_TEMPORAL_CHECKS,
    **_V1_6_02_FORECAST_CHECKS,
    **_V1_6_02_VALUATION_CHECKS,
    **_V1_6_02_DECISION_CHECKS,
    **_RELEASE_GOVERNANCE_CHECKS,
}

PACK_REGISTRY: Mapping[str, VerificationPack] = {
    "m1-core-runtime": VerificationPack(
        pack_id="m1-core-runtime",
        check_ids=tuple(_BASELINE_CHECKS),
    ),
    "m2-persistence-http": VerificationPack(
        pack_id="m2-persistence-http",
        check_ids=tuple(_M2_PERSISTENCE_HTTP_CHECKS),
    ),
    "m3-professional-foundations": VerificationPack(
        pack_id="m3-professional-foundations",
        check_ids=tuple(_M3_PROFESSIONAL_FOUNDATIONS_CHECKS),
    ),
    "m4-reporting-replay": VerificationPack(
        pack_id="m4-reporting-replay",
        check_ids=tuple(_M4_REPORTING_REPLAY_CHECKS),
    ),
    "m5-quality-release": VerificationPack(
        pack_id="m5-quality-release",
        check_ids=tuple(_M5_QUALITY_RELEASE_CHECKS),
    ),
    "v1-6-01-professional-closure": VerificationPack(
        pack_id="v1-6-01-professional-closure",
        check_ids=tuple(_V1_6_01_PROFESSIONAL_CLOSURE_CHECKS),
    ),
    "v1-6-02-temporal-sufficiency": VerificationPack(
        pack_id="v1-6-02-temporal-sufficiency",
        check_ids=tuple(_V1_6_02_TEMPORAL_CHECKS),
    ),
    "v1-6-02-forecast-benchmark": VerificationPack(
        pack_id="v1-6-02-forecast-benchmark",
        check_ids=tuple(_V1_6_02_FORECAST_CHECKS),
    ),
    "v1-6-02-valuation-market-gap": VerificationPack(
        pack_id="v1-6-02-valuation-market-gap",
        check_ids=tuple(_V1_6_02_VALUATION_CHECKS),
    ),
    "v1-6-02-decision-context": VerificationPack(
        pack_id="v1-6-02-decision-context",
        check_ids=tuple(_V1_6_02_DECISION_CHECKS),
    ),
    "release-governance": VerificationPack(
        pack_id="release-governance",
        check_ids=tuple(_RELEASE_GOVERNANCE_CHECKS),
    ),
}


def resolve_release_checks(manifest: ReleaseManifest) -> dict[str, str]:
    """Resolve manifest-selected packs into one ordered, fail-closed check map."""

    resolved: dict[str, str] = {}
    for pack_id in manifest.verification_packs:
        try:
            pack = PACK_REGISTRY[pack_id]
        except KeyError as exc:
            raise ValueError(f"unknown verification pack: {pack_id}") from exc
        for check_id in pack.check_ids:
            if check_id in resolved:
                raise ValueError(f"duplicate verification check: {check_id}")
            try:
                resolved[check_id] = CHECK_REGISTRY[check_id]
            except KeyError as exc:
                raise ValueError(
                    f"verification pack {pack_id!r} references unknown check {check_id!r}"
                ) from exc
    if not resolved:
        raise ValueError("release must select at least one verification check")
    return resolved
