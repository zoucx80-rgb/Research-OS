import json
import tomllib
from pathlib import Path

import research_os
from research_os.release.runtime import CHECKS
from research_os.reporting import ResearchReportComposer, ResearchViewPresenter
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


V1_5_05_CHECKS = {
    "report_composer_one_way": "tests/unit/reporting/test_composer.py::test_composer_rejects_raw_objects_instead_of_becoming_second_semantic_path",
    "expectation_gap_missingness": "tests/unit/expectations/test_expectation_gap.py::test_missing_consensus_does_not_fabricate_gap",
    "valuation_result_contract": "tests/unit/valuation/test_result_contract.py::test_valuation_result_carries_scenarios_ranges_and_lineage",
    "composition_dedup": "tests/unit/reporting/test_composition_rules.py::test_repeated_economic_risks_are_deduplicated_by_semantic_code",
    "lease_heavy_presentation_guard": "tests/regression/research_patterns/test_v1_5_05_reporting_patterns.py::test_lease_heavy_hospitality_without_plugin_surfaces_capability_break_and_no_fake_hotel_kpis",
    "audit_metadata_separation": "tests/unit/reporting/test_monitoring_and_evidence.py::test_main_body_evidence_note_is_concise_and_raw_ids_stay_in_audit_appendix",
}


def test_public_v1_5_05_version_and_reporting_fingerprints_are_consistent():
    project = tomllib.loads(Path("pyproject.toml").read_text())
    metadata = json.loads(Path("research_os_version.json").read_text())

    assert tuple(map(int, RESEARCH_OS_VERSION.split("."))) >= (1, 5, 5)
    assert research_os.__version__ == RESEARCH_OS_VERSION
    assert project["project"]["version"] == RESEARCH_OS_VERSION
    assert metadata["research_os_version"] == RESEARCH_OS_VERSION
    assert metadata["status"] in {"release_candidate", "stable"}
    assert CORE_API_VERSION == "1.0"
    assert metadata["core_api_version"] == "1.0"
    assert metadata["module_versions"]["semantic_research_view"] == "1.3.0"
    assert tuple(map(int, metadata["module_versions"]["report_composer"].split("."))) >= (1, 0, 0)
    assert ResearchViewPresenter.version == "professional-research-view@1.3.0"
    composer_version = ResearchReportComposer.version.rsplit("@", 1)[-1]
    assert tuple(map(int, composer_version.split("."))) >= (1, 0, 0)


def test_release_gate_contains_v1_5_05_reporting_checks():
    for gate, nodeid in V1_5_05_CHECKS.items():
        assert CHECKS.get(gate) == nodeid
        assert Path(nodeid.split("::", 1)[0]).exists()


def test_v1_5_05_release_documentation_exists_and_preserves_one_way_boundary():
    migration = Path("docs/migrations/v1.5.05.md")
    readme = Path("README.md").read_text()
    changelog = Path("CHANGELOG.md").read_text()
    protocol = Path("docs/prompts/stock_research.md").read_text()

    assert migration.exists()
    assert "v1.5.05" in readme
    assert "1.5.5" in changelog
    assert "ResearchReportComposer" in migration.read_text()
    assert "ResearchRunResult" in migration.read_text()
    assert "HumanReadableResearchView" in migration.read_text()
    assert "ResearchReportDocument" in migration.read_text()
    assert "professional-research-view@1.3.0" in protocol
    assert "research-report-composer@1.0.0" in protocol
