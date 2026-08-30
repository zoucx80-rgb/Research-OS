import json
import tomllib
from pathlib import Path

import research_os
from research_os.plugins.builtins import DistributorIndustryPlugin
from research_os.release.runtime import CHECKS
from research_os.reporting.research_view import ResearchViewPresenter
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


V1_5_04_CHECKS = {
    "reported_yoy_rounding": "tests/regression/research_patterns/test_v1_5_04_field_correctness.py::test_reported_yoy_rounding_does_not_fail_financial_sanity",
    "canonical_ocf_falsifier": "tests/regression/research_patterns/test_v1_5_04_field_correctness.py::test_negative_ocf_triggers_cash_thesis_falsifier_and_limits_lineage",
    "explicit_equity_financing": "tests/regression/research_patterns/test_v1_5_04_field_correctness.py::test_book_equity_change_is_not_external_financing_or_dilution",
    "delta_comparison_basis": "tests/regression/research_patterns/test_v1_5_04_field_correctness.py::test_incomparable_delta_bases_do_not_produce_incremental_ratios",
    "funding_aware_pe_fitness": "tests/regression/research_patterns/test_v1_5_04_field_correctness.py::test_debt_funded_negative_ocf_distributor_cannot_route_pe_as_primary",
    "material_artifact_projection": "tests/regression/research_patterns/test_v1_5_04_field_correctness.py::test_professional_view_projects_material_canonical_artifacts",
}


def test_public_v1_5_04_version_and_component_fingerprints_are_consistent():
    project = tomllib.loads(Path("pyproject.toml").read_text())
    metadata = json.loads(Path("research_os_version.json").read_text())

    assert tuple(map(int, RESEARCH_OS_VERSION.split("."))) >= (1, 5, 4)
    assert research_os.__version__ == RESEARCH_OS_VERSION
    assert project["project"]["version"] == RESEARCH_OS_VERSION
    assert metadata["research_os_version"] == RESEARCH_OS_VERSION
    assert metadata["status"] in {"release_candidate", "stable"}
    assert CORE_API_VERSION == "1.0"
    assert metadata["core_api_version"] == "1.0"
    assert metadata["module_versions"]["period_semantics"] == "1.1.0"
    assert metadata["module_versions"]["driver_engine"] == "1.3.0"
    assert metadata["module_versions"]["thesis_engine"] == "1.2.0"
    assert metadata["module_versions"]["valuation"] == "2.2.0"
    assert tuple(map(int, metadata["module_versions"]["semantic_research_view"].split("."))) >= (1, 2, 0)
    assert ResearchViewPresenter.version == "professional-research-view@1.2.0"
    assert DistributorIndustryPlugin.manifest.plugin_version == "1.2.0"


def test_release_gate_contains_v1_5_04_field_correctness_checks():
    for gate, nodeid in V1_5_04_CHECKS.items():
        assert CHECKS.get(gate) == nodeid
        assert Path(nodeid.split("::", 1)[0]).exists()


def test_v1_5_04_release_documentation_exists_and_preserves_patch_boundaries():
    migration = Path("docs/migrations/v1.5.04.md")
    readme = Path("README.md").read_text()
    changelog = Path("CHANGELOG.md").read_text()
    protocol = Path("docs/prompts/stock_research.md").read_text()
    spec = Path("docs/superpowers/specs/2026-08-30-research-os-v1-5-04-field-correctness-design.md").read_text()

    assert migration.exists()
    assert "v1.5.04" in readme
    assert "1.5.4" in changelog
    assert "comparison basis" in migration.read_text().lower()
    assert "professional-research-view@1.2.0" in protocol
    assert "no Hospitality Plugin" in spec
    assert "Core API remains `1.0`" in spec
