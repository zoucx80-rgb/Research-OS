import json
import tomllib
from pathlib import Path

import research_os
from research_os.release.runtime import CHECKS
from research_os.reporting.semantics import DecisionSummaryPresenter
from research_os.router.classifier import BusinessModelRouter
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


V1_5_01_GATES = {
    "router_period_semantics": "tests/unit/router/test_classifier.py::test_interim_inventory_to_revenue_does_not_add_distributor_score",
    "business_model_gap_semantics": "tests/unit/plugins/test_resolver.py::test_resolver_distinguishes_unsupported_taxonomy_from_missing_plugin",
    "human_readable_reporting": "tests/unit/reporting/test_semantics.py::test_presenter_keeps_machine_code_secondary_and_chinese_label_primary",
    "presentation_single_source": "tests/unit/reporting/test_semantics.py::test_presenter_does_not_recompute_completion_or_decision_state",
}


def test_public_v1_5_01_version_and_core_api_are_consistent():
    project = tomllib.loads(Path("pyproject.toml").read_text())
    metadata = json.loads(Path("research_os_version.json").read_text())

    assert RESEARCH_OS_VERSION == "1.5.1"
    assert research_os.__version__ == "1.5.1"
    assert project["project"]["version"] == "1.5.1"
    assert metadata["research_os_version"] == "1.5.1"
    assert CORE_API_VERSION == "1.0"
    assert metadata["core_api_version"] == "1.0"
    assert metadata["module_versions"]["router"] == "1.1.0"
    assert metadata["module_versions"]["semantic_presentation"] == "1.0.0"
    assert BusinessModelRouter.version == "router@1.1.0"
    assert DecisionSummaryPresenter.version == "semantic-report@1.0.0"


def test_release_gate_contains_v1_5_01_semantic_correctness_checks():
    for gate, nodeid in V1_5_01_GATES.items():
        assert CHECKS.get(gate) == nodeid
        assert Path(nodeid.split("::", 1)[0]).exists()


def test_v1_5_01_release_documentation_exists():
    migration = Path("docs/migrations/v1.5.01.md")
    readme = Path("README.md").read_text()
    changelog = Path("CHANGELOG.md").read_text()

    assert migration.exists()
    assert "v1.5.01" in readme
    assert "1.5.1" in changelog
    assert "DecisionSummaryPresenter" in migration.read_text()
    assert "ResearchCompletionGate" in migration.read_text()
