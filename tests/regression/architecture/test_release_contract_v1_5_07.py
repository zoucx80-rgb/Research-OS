import json
import tomllib
from pathlib import Path

import research_os
from research_os.release.runtime import CHECKS
from research_os.reporting import (
    ResearchReportComposer,
    ResearchReportMarkdownRenderer,
    ResearchViewPresenter,
)
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


V1_5_07_CHECKS = {
    "markdown_renderer_v1_5_07": "tests/unit/reporting/test_markdown_renderer.py",
    "renderer_cross_model_v1_5_07": "tests/regression/research_patterns/test_v1_5_07_renderer_patterns.py",
}


def test_public_v1_5_07_version_and_reporting_fingerprints_are_consistent():
    project = tomllib.loads(Path("pyproject.toml").read_text())
    metadata = json.loads(Path("research_os_version.json").read_text())

    assert RESEARCH_OS_VERSION == "1.5.7"
    assert research_os.__version__ == "1.5.7"
    assert project["project"]["version"] == "1.5.7"
    assert metadata["research_os_version"] == "1.5.7"
    assert metadata["status"] == "stable"
    assert CORE_API_VERSION == "1.0"
    assert metadata["core_api_version"] == "1.0"
    assert metadata["module_versions"]["semantic_research_view"] == "1.3.0"
    assert metadata["module_versions"]["report_composer"] == "1.1.0"
    assert metadata["module_versions"]["markdown_renderer"] == "1.0.0"
    assert ResearchViewPresenter.version == "professional-research-view@1.3.0"
    assert ResearchReportComposer.version == "research-report-composer@1.1.0"
    assert ResearchReportMarkdownRenderer.version == "professional-markdown-renderer@1.0.0"


def test_release_gate_contains_v1_5_07_renderer_checks():
    for gate, nodeid in V1_5_07_CHECKS.items():
        assert CHECKS.get(gate) == nodeid
        assert Path(nodeid.split("::", 1)[0]).exists()


def test_v1_5_07_release_documentation_exists_and_preserves_renderer_boundary():
    migration = Path("docs/migrations/v1.5.07.md")
    readme = Path("README.md").read_text()
    changelog = Path("CHANGELOG.md").read_text()
    protocol = Path("docs/prompts/stock_research.md").read_text()

    assert migration.exists()
    assert "v1.5.07" in readme
    assert "1.5.7" in changelog
    migration_text = migration.read_text()
    assert "ResearchReportDocument" in migration_text
    assert "ResearchReportMarkdownRenderer" in migration_text
    assert "不重新计算" in migration_text
    assert "professional-markdown-renderer@1.0.0" in protocol
