import json
from pathlib import Path

import research_os
from research_os.plugins.builtins import DistributorIndustryPlugin, ManufacturingIndustryPlugin
from research_os.release.runtime import CHECKS
from research_os.reporting import ResearchViewPresenter
from research_os.router.classifier import BusinessModelRouter
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


V1_5_03_GATES = {
    "state_provenance": "tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_legacy_high_level_states_are_exposed_as_analyst_assumptions",
    "driver_specific_lineage": "tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_manufacturing_driver_lineage_is_fact_specific_and_includes_supported_working_capital_nodes",
    "evidence_driven_thesis": "tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_manufacturing_mixed_signals_do_not_assert_fundamentals_improve",
    "professional_question_coverage": "tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_builtin_industry_questions_have_structured_capability_and_evidence_contract",
    "event_relative_expectations": "tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_consensus_predating_material_event_is_low_quality_even_when_calendar_fresh",
    "lease_aware_router": "tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_material_right_of_use_assets_suppress_low_ppe_distributor_heuristic",
    "working_capital_financing_exposure": "tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_distributor_pack_exposes_factoring_and_total_financing_burden_without_relabeling_as_debt",
    "quantitative_presentation_semantics": "tests/regression/research_patterns/test_v1_5_03_professional_integrity.py::test_human_readable_metric_formats_percentage_days_and_period_semantics",
}


def test_v1_5_03_component_contract_remains_available():
    metadata = json.loads(Path("research_os_version.json").read_text())

    assert tuple(map(int, RESEARCH_OS_VERSION.split("."))) >= (1, 5, 3)
    assert research_os.__version__ == RESEARCH_OS_VERSION
    assert metadata["research_os_version"] == RESEARCH_OS_VERSION
    assert metadata["status"] == "stable"
    assert CORE_API_VERSION == "1.0"
    assert metadata["core_api_version"] == "1.0"
    assert BusinessModelRouter.version == "router@1.2.0"
    assert metadata["module_versions"]["router"] == "1.2.0"
    assert tuple(map(int, metadata["module_versions"]["driver_engine"].split("."))) >= (1, 2, 0)
    assert tuple(map(int, metadata["module_versions"]["thesis_engine"].split("."))) >= (1, 1, 0)
    assert tuple(map(int, metadata["module_versions"]["expectation_engine"].split("."))) >= (1, 2, 0)
    assert tuple(map(int, metadata["module_versions"]["semantic_research_view"].split("."))) >= (1, 1, 0)
    assert tuple(map(int, ResearchViewPresenter.version.rsplit("@", 1)[1].split("."))) >= (1, 1, 0)
    assert ManufacturingIndustryPlugin.manifest.plugin_version == "1.1.0"
    assert tuple(map(int, DistributorIndustryPlugin.manifest.plugin_version.split("."))) >= (1, 1, 0)


def test_release_gate_contains_v1_5_03_professional_integrity_checks():
    for gate, nodeid in V1_5_03_GATES.items():
        assert CHECKS.get(gate) == nodeid
        assert Path(nodeid.split("::", 1)[0]).exists()


def test_v1_5_03_release_documentation_exists_and_preserves_boundaries():
    migration = Path("docs/migrations/v1.5.03.md")
    readme = Path("README.md").read_text()
    changelog = Path("CHANGELOG.md").read_text()
    protocol = Path("docs/prompts/stock_research.md").read_text()
    spec = Path("docs/superpowers/specs/2026-08-30-research-os-v1-5-03-professional-research-integrity-design.md").read_text()
    plan = Path("docs/superpowers/plans/2026-08-30-research-os-v1-5-03-professional-research-integrity.md").read_text()

    assert migration.exists()
    assert "v1.5.03" in readme
    assert "1.5.3" in changelog
    assert "State Provenance" in migration.read_text()
    assert "professional-research-view@1.1.0" in protocol
    assert "Hospitality Plugin" in spec
    assert "lease-adjusted valuation" in spec
    assert "Completion" in plan
