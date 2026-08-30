from __future__ import annotations
import subprocess, sys
from pathlib import Path
from collections.abc import Callable, Iterable


CHECKS: dict[str,str]={
    "v1_golden":"tests/golden/test_v1_0_manufacturing_reproducibility.py",
    "pit":"tests/golden/test_no_time_travel.py",
    "manufacturing":"tests/golden/kpi/test_manufacturing_pack.py",
    "distributor":"tests/integration/test_canonical_research_runtime.py::test_canonical_distributor_run_is_auditable_and_carries_metric_lineage",
    "router_explainable":"tests/unit/router/test_classifier.py::test_router_classifies_high_inventory_low_fixed_asset_company_as_distributor",
    "thesis_falsifiers":"tests/unit/thesis/test_state_machine.py::test_active_thesis_requires_explicit_anti_thesis",
    "ledger":"tests/unit/ledger/test_ledger.py::test_material_research_conclusion_requires_expiry_and_next_verification",
    "valuation_fitness":"tests/unit/valuation/test_router.py::test_low_fitness_model_cannot_dominate_primary_models",
    "decision_no_trade":"tests/unit/decision/test_models.py::test_decision_state_is_research_only",
    "snapshot_reproducible":"tests/unit/snapshots/test_snapshot_service.py::test_snapshot_freezes_payload_with_verifiable_hash",
    "repository_preflight":"tests/unit/preflight/test_validator.py",
    "evidence_lineage":"tests/unit/domain/test_lineage_contracts.py",
    "financial_sanity":"tests/unit/validation/test_financial_sanity.py",
    "expectation_evidence":"tests/unit/expectations/test_evidence_gate.py",
    "valuation_execution":"tests/unit/valuation/test_execution.py",
    "decision_validation":"tests/unit/decision/test_validation.py",
    "completion_gate":"tests/unit/completion/test_gate.py",
    "temporal_consistency":"tests/unit/events/test_temporal_validation.py",
    "distributor_kpi_safety":"tests/unit/kpi/test_distributor_safety_metrics.py",
    "research_completion_integration":"tests/integration/test_runtime_safety_inputs.py::test_full_typed_safety_inputs_can_produce_complete_machine_run",
    "migration_lineage":"tests/integration/storage/test_v1_2_lineage_migration.py",
    "period_semantics":"tests/unit/kpi/test_period_sensitive_packs.py",
    "missing_value_semantics":"tests/unit/capital/test_engine.py::test_negative_ocf_without_funding_inputs_does_not_invent_funding_state",
    "kpi_applicability":"tests/unit/kpi/test_applicability.py",
    "completion_consistency":"tests/unit/completion/test_consistency.py",
    "version_consistency":"tests/unit/test_version_consistency_v1_2_1.py",
    "research_context_contract":"tests/unit/runtime/test_context.py",
    "research_inputs_contract":"tests/unit/runtime/test_inputs.py",
    "module_contract":"tests/unit/runtime/test_engine.py::test_engine_rejects_undeclared_artifact_from_module",
    "pipeline_dependency_resolution":"tests/unit/runtime/test_engine.py::test_engine_orders_modules_by_capability_dependencies_deterministically",
    "plugin_manifest_contract":"tests/unit/plugins/test_manifest_contract.py",
    "plugin_compatibility_resolution":"tests/unit/plugins/test_registry.py",
    "industry_auto_resolution":"tests/unit/plugins/test_builtin_industry_plugins.py",
    "methodology_auto_resolution":"tests/unit/plugins/test_resolver.py",
    "unsupported_coverage_gap":"tests/unit/plugins/test_resolver.py",
    "plugin_failure_isolation":"tests/unit/runtime/test_engine.py::test_engine_wraps_module_exception_with_module_identity",
    "canonical_runtime_entrypoint":"tests/integration/runtime/test_canonical_runtime.py",
    "canonical_result_contract":"tests/unit/runtime/test_result.py",
    "knowledge_interface_pit":"tests/unit/knowledge/test_provider.py",
    "snapshot_component_fingerprints":"tests/integration/runtime/test_snapshot_component_fingerprints.py",
    "completion_single_source_v1_4":"tests/unit/reporting/test_canonical_result_source.py",
    "core_api_version_consistency":"tests/regression/architecture/test_release_contract_v1_4.py::test_public_release_version_and_core_api_are_consistent",
    "extensibility_no_engine_change":"tests/regression/architecture/test_extensibility.py",
    "no_legacy_runtime_policy_duplication":"tests/regression/architecture/test_single_runtime_policy.py",
    "router_period_semantics":"tests/unit/router/test_classifier.py::test_interim_inventory_to_revenue_does_not_add_distributor_score",
    "business_model_gap_semantics":"tests/unit/plugins/test_resolver.py::test_resolver_distinguishes_unsupported_taxonomy_from_missing_plugin",
    "human_readable_reporting":"tests/unit/reporting/test_semantics.py::test_presenter_keeps_machine_code_secondary_and_chinese_label_primary",
    "presentation_single_source":"tests/unit/reporting/test_semantics.py::test_presenter_does_not_recompute_completion_or_decision_state",
}

ROOT=Path(__file__).resolve().parents[3]


def _pytest_runner(nodeid:str)->bool:
    result=subprocess.run([sys.executable,"-m","pytest","-q",nodeid],cwd=ROOT,capture_output=True,text=True)
    return result.returncode==0


def _pytest_batch_runner(nodeids:Iterable[str])->bool:
    result=subprocess.run([sys.executable,"-m","pytest","-q",*nodeids],cwd=ROOT,capture_output=True,text=True)
    return result.returncode==0


def run_release_checks(runner:Callable[[str],bool]|None=None,batch_runner:Callable[[Iterable[str]],bool]|None=None)->dict[str,bool]:
    if runner is not None:
        return {name:bool(runner(nodeid)) for name,nodeid in CHECKS.items()}
    batch=batch_runner or _pytest_batch_runner
    passed=bool(batch(CHECKS.values()))
    return {name:passed for name in CHECKS}
