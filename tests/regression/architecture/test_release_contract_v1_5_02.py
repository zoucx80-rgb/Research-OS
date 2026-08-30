import json
import tomllib
from pathlib import Path

import research_os
from research_os.release.runtime import CHECKS
from research_os.reporting import ResearchViewPresenter
from research_os.router.classifier import BusinessModelRouter
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


V1_5_02_GATES = {
    "business_model_status_truth": "tests/regression/research_patterns/test_v1_5_02_semantic_integrity.py::test_unresolved_business_model_does_not_report_router_pass",
    "coverage_aware_thesis": "tests/regression/research_patterns/test_v1_5_02_semantic_integrity.py::test_missing_primary_industry_coverage_keeps_generic_drivers_but_blocks_active_thesis",
    "funding_material_risk": "tests/regression/research_patterns/test_v1_5_02_semantic_integrity.py::test_debt_funded_negative_ocf_is_material_risk_for_decision_state",
    "expectation_quality": "tests/regression/research_patterns/test_v1_5_02_semantic_integrity.py::test_expectation_quality_uses_existing_consensus_fields_and_age",
    "industry_report_contributions": "tests/regression/research_patterns/test_v1_5_02_semantic_integrity.py::test_builtin_industry_plugins_provide_structured_report_contributions",
    "primary_industry_isolation": "tests/regression/research_patterns/test_v1_5_02_semantic_integrity.py::test_secondary_industry_plugin_cannot_contaminate_primary_kpi_pack",
    "end_to_end_research_view": "tests/unit/reporting/test_research_view.py::test_distributor_research_view_humanizes_end_to_end_machine_artifacts",
    "coverage_limited_completion": "tests/unit/reporting/test_research_view.py::test_hospitality_research_view_exposes_coverage_limit_without_fake_thesis",
}


def _version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("."))


def test_public_v1_5_02_version_and_core_api_are_consistent():
    project = tomllib.loads(Path("pyproject.toml").read_text())
    metadata = json.loads(Path("research_os_version.json").read_text())

    assert _version_tuple(RESEARCH_OS_VERSION) >= (1, 5, 2)
    assert research_os.__version__ == RESEARCH_OS_VERSION
    assert project["project"]["version"] == RESEARCH_OS_VERSION
    assert metadata["research_os_version"] == RESEARCH_OS_VERSION
    assert CORE_API_VERSION == "1.0"
    assert metadata["core_api_version"] == "1.0"
    assert _version_tuple(metadata["module_versions"]["router"]) >= (1, 1, 0)
    assert metadata["module_versions"]["router"] == BusinessModelRouter.version.rsplit("@", 1)[-1]
    assert metadata["module_versions"]["semantic_presentation"] == "1.0.0"
    assert _version_tuple(metadata["module_versions"]["semantic_research_view"]) >= (1, 0, 0)
    assert ResearchViewPresenter.version.startswith("semantic-research-view@")


def test_release_gate_contains_v1_5_02_semantic_integrity_checks():
    for gate, nodeid in V1_5_02_GATES.items():
        assert CHECKS.get(gate) == nodeid
        assert Path(nodeid.split("::", 1)[0]).exists()


def test_v1_5_02_release_documentation_exists():
    migration = Path("docs/migrations/v1.5.02.md")
    readme = Path("README.md").read_text()
    changelog = Path("CHANGELOG.md").read_text()
    protocol = Path("docs/prompts/stock_research.md").read_text()
    design = Path("docs/superpowers/specs/2026-08-30-research-os-v1-5-02-semantic-research-integrity-design.md").read_text()

    assert migration.exists()
    assert "v1.5.02" in readme
    assert "1.5.2" in changelog
    assert "ResearchViewPresenter" in migration.read_text()
    assert "ResearchCompletionGate" in migration.read_text()
    assert "ResearchViewPresenter" in protocol
    assert "primary business model" in design.lower()
    assert "secondary" in design.lower()
