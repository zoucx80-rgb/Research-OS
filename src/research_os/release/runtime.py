from __future__ import annotations
import os
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
    "business_model_status_truth":"tests/regression/research_patterns/test_v1_5_02_semantic_integrity.py::test_unresolved_business_model_does_not_report_router_pass",
    "coverage_aware_thesis":"tests/regression/research_patterns/test_v1_5_02_semantic_integrity.py::test_missing_primary_industry_coverage_keeps_generic_drivers_but_blocks_active_thesis",
    "funding_material_risk":"tests/regression/research_patterns/test_v1_5_02_semantic_integrity.py::test_debt_funded_negative_ocf_is_material_risk_for_decision_state",
    "expectation_quality":"tests/regression/research_patterns/test_v1_5_02_semantic_integrity.py::test_expectation_quality_uses_existing_consensus_fields_and_age",
    "industry_report_contributions":"tests/regression/research_patterns/test_v1_5_02_semantic_integrity.py::test_builtin_industry_plugins_provide_structured_report_contributions",
    "primary_industry_isolation":"tests/regression/research_patterns/test_v1_5_02_semantic_integrity.py::test_secondary_industry_plugin_cannot_contaminate_primary_kpi_pack",
    "end_to_end_research_view":"tests/unit/reporting/test_research_view.py::test_distributor_research_view_humanizes_end_to_end_machine_artifacts",
    "coverage_limited_completion":"tests/unit/reporting/test_research_view.py::test_hospitality_research_view_exposes_coverage_limit_without_fake_thesis",
    "state_provenance":"tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_legacy_high_level_states_are_exposed_as_analyst_assumptions",
    "driver_specific_lineage":"tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_manufacturing_driver_lineage_is_fact_specific_and_includes_supported_working_capital_nodes",
    "evidence_driven_thesis":"tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_manufacturing_mixed_signals_do_not_assert_fundamentals_improve",
    "professional_question_coverage":"tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_builtin_industry_questions_have_structured_capability_and_evidence_contract",
    "event_relative_expectations":"tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_consensus_predating_material_event_is_low_quality_even_when_calendar_fresh",
    "lease_aware_router":"tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_material_right_of_use_assets_suppress_low_ppe_distributor_heuristic",
    "working_capital_financing_exposure":"tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_distributor_pack_exposes_factoring_and_total_financing_burden_without_relabeling_as_debt",
    "quantitative_presentation_semantics":"tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_human_readable_metric_formats_percentage_days_and_period_semantics",
    "reported_yoy_rounding":"tests/regression/research_patterns/test_v1_5_04_field_correctness.py::test_reported_yoy_rounding_does_not_fail_financial_sanity",
    "canonical_ocf_falsifier":"tests/regression/research_patterns/test_v1_5_04_field_correctness.py::test_negative_ocf_triggers_cash_thesis_falsifier_and_limits_lineage",
    "explicit_equity_financing":"tests/regression/research_patterns/test_v1_5_04_field_correctness.py::test_book_equity_change_is_not_external_financing_or_dilution",
    "delta_comparison_basis":"tests/regression/research_patterns/test_v1_5_04_field_correctness.py::test_incomparable_delta_bases_do_not_produce_incremental_ratios",
    "funding_aware_pe_fitness":"tests/regression/research_patterns/test_v1_5_04_field_correctness.py::test_debt_funded_negative_ocf_distributor_cannot_route_pe_as_primary",
    "material_artifact_projection":"tests/regression/research_patterns/test_v1_5_04_field_correctness.py::test_professional_view_projects_material_canonical_artifacts",
    "report_composer_one_way":"tests/unit/reporting/test_composer.py::test_composer_rejects_raw_objects_instead_of_becoming_second_semantic_path",
    "expectation_gap_missingness":"tests/unit/expectations/test_expectation_gap.py::test_missing_consensus_does_not_fabricate_gap",
    "valuation_result_contract":"tests/unit/valuation/test_result_contract.py::test_valuation_result_carries_scenarios_ranges_and_lineage",
    "composition_dedup":"tests/unit/reporting/test_composition_rules.py::test_repeated_economic_risks_are_deduplicated_by_semantic_code",
    "lease_heavy_presentation_guard":"tests/regression/research_patterns/test_v1_5_05_reporting_patterns.py::test_lease_heavy_hospitality_without_plugin_surfaces_capability_break_and_no_fake_hotel_kpis",
    "audit_metadata_separation":"tests/unit/reporting/test_monitoring_and_evidence.py::test_main_body_evidence_note_is_concise_and_raw_ids_stay_in_audit_appendix",
    "composition_coverage_v1_5_06":"tests/unit/reporting/test_composition_coverage_v1_5_06.py",
    "markdown_renderer_v1_5_07":"tests/unit/reporting/test_markdown_renderer.py",
    "renderer_cross_model_v1_5_07":"tests/regression/research_patterns/test_v1_5_07_renderer_patterns.py",
    "presentation_artifacts_v1_5_08":"tests/unit/presentation",
    "professional_presentation_pipeline_v1_5_08":"tests/regression/research_patterns/test_v1_5_08_presentation_patterns.py",
    "presentation_dependency_boundary_v1_5_08":"tests/regression/architecture/test_presentation_dependency_boundary.py",
    "playwright_pdf_v1_5_08":"tests/integration/presentation/test_playwright_pdf_adapter.py",
    "field_acceptance_v1_5_08":"tests/integration/presentation/test_field_acceptance_runner.py",
    "financial_fact_snapshot_v1_5_09":"tests/unit/runtime/test_financial_fact_snapshot_v1_5_09.py",
    "research_depth_semantics_v1_5_09":"tests/unit/reporting/test_research_depth_semantics_v1_5_09.py",
    "professional_output_depth_v1_5_09":"tests/unit/reporting/test_professional_output_depth_v1_5_09.py",
    "dual_field_acceptance_v1_5_09":"tests/integration/presentation/test_field_acceptance_v1_5_09.py",
    "three_company_field_depth_v1_5_09":"tests/regression/research_patterns/test_v1_5_09_field_depth_patterns.py",
    "release_contract_v1_5_09":"tests/regression/architecture/test_release_contract_v1_5_09.py",
    "research_completeness_contracts_v1_5_10":"tests/unit/completeness/test_models_and_services.py",
    "research_completeness_runtime_v1_5_10":"tests/unit/runtime/test_research_completeness_v1_5_10.py",
    "research_completeness_reporting_v1_5_10":"tests/unit/reporting/test_research_completeness_v1_5_10.py",
    "research_completeness_field_v1_5_10":"tests/integration/presentation/test_field_acceptance_v1_5_10.py",
    "research_completeness_patterns_v1_5_10":"tests/regression/research_patterns/test_v1_5_10_research_completeness.py",
    "release_contract_v1_5_10":"tests/regression/architecture/test_release_contract_v1_5_10.py",
}

ROOT=Path(__file__).resolve().parents[3]


def _pytest_runner(nodeid:str)->bool:
    env=os.environ.copy()
    env["RESEARCH_OS_RUN_PDF_INTEGRATION"] = "1"
    result=subprocess.run([sys.executable,"-m","pytest","-q",nodeid],cwd=ROOT,capture_output=True,text=True,env=env)
    return result.returncode==0


def _pytest_batch_runner(nodeids:Iterable[str])->bool:
    env=os.environ.copy()
    env["RESEARCH_OS_RUN_PDF_INTEGRATION"] = "1"
    result=subprocess.run([sys.executable,"-m","pytest","-q",*nodeids],cwd=ROOT,capture_output=True,text=True,env=env)
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    return result.returncode==0


def run_release_checks(runner:Callable[[str],bool]|None=None,batch_runner:Callable[[Iterable[str]],bool]|None=None)->dict[str,bool]:
    if runner is not None:
        return {name:bool(runner(nodeid)) for name,nodeid in CHECKS.items()}
    batch=batch_runner or _pytest_batch_runner
    passed=bool(batch(CHECKS.values()))
    return {name:passed for name in CHECKS}
