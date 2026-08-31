from __future__ import annotations

import json
from pathlib import Path
import tomllib

from research_os.presentation import PlaywrightPdfAdapter, ProfessionalHtmlRenderer
from research_os.release.replays import REPLAY_REGISTRY
from research_os.release.runtime import CHECKS
from research_os.reporting.composer import ResearchReportComposer
from research_os.reporting.markdown_renderer import ResearchReportMarkdownRenderer
from research_os.reporting.research_view_v1_5_05 import ResearchViewPresenter
from research_os.version import CORE_API_VERSION


V1_5_08_CHECKS = {
    "presentation_artifacts_v1_5_08": "tests/unit/presentation",
    "professional_presentation_pipeline_v1_5_08": (
        "tests/regression/research_patterns/test_v1_5_08_presentation_patterns.py"
    ),
    "presentation_dependency_boundary_v1_5_08": (
        "tests/regression/architecture/test_presentation_dependency_boundary.py"
    ),
    "playwright_pdf_v1_5_08": (
        "tests/integration/presentation/test_playwright_pdf_adapter.py"
    ),
    "field_acceptance_v1_5_08": (
        "tests/integration/presentation/test_field_acceptance_runner.py"
    ),
}


def test_historical_v1_5_08_presentation_fingerprints_remain_replayable():
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    metadata = json.loads(Path("research_os_version.json").read_text(encoding="utf-8"))

    assert CORE_API_VERSION == "1.0"
    assert metadata["core_api_version"] == "1.0"
    assert project["project"]["optional-dependencies"]["pdf"] == [
        "playwright>=1.62,<1.63"
    ]
    assert ResearchViewPresenter.version == "professional-research-view@1.3.0"
    assert ResearchReportComposer.version == "research-report-composer@1.1.0"
    assert ResearchReportMarkdownRenderer.version == "professional-markdown-renderer@1.0.0"
    assert ProfessionalHtmlRenderer.version == "professional-html-renderer@1.0.0"
    assert PlaywrightPdfAdapter.version == "professional-pdf-adapter@1.0.0"


def test_playwright_is_an_optional_pdf_dependency_only():
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert all("playwright" not in item for item in project["project"]["dependencies"])
    assert project["project"]["optional-dependencies"]["pdf"] == [
        "playwright>=1.62,<1.63"
    ]
    assert "pypdf>=6,<7" in project["project"]["optional-dependencies"]["test"]


def test_release_gate_requires_v1_5_08_pipeline_and_real_browser_pdf():
    for gate, nodeid in V1_5_08_CHECKS.items():
        assert CHECKS.get(gate) == nodeid
        assert Path(nodeid.split("::", 1)[0]).exists()


def test_v1_5_08_field_acceptance_is_a_frozen_replay_profile():
    profile = REPLAY_REGISTRY["field-v1.5.08"]
    assert profile.frozen is True
    assert profile.runner_script == "scripts/render_field_acceptance_v1_5_08.py"
    assert profile.fixture_dir == "tests/fixtures/field_acceptance/v1_5_08"
    assert Path(profile.runner_script).exists()
    assert Path(profile.fixture_dir).exists()


def test_v1_5_08_documentation_preserves_one_way_boundary_and_non_goals():
    migration = Path("docs/migrations/v1.5.08.md")
    readme = Path("README.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    protocol = Path("docs/prompts/stock_research.md").read_text(encoding="utf-8")

    assert migration.exists()
    migration_text = migration.read_text(encoding="utf-8")
    for text in (
        "MarkdownPresentationArtifact",
        "HtmlPresentationArtifact",
        "PdfPresentationArtifact",
        "professional-html-renderer@1.0.0",
        "professional-pdf-adapter@1.0.0",
        "不重新计算",
        "Factoring",
    ):
        assert text in migration_text
    assert "Research OS v1.5.08" in readme
    assert "## 1.5.8" in changelog
    assert "professional-html-renderer@1.0.0" in protocol
    assert "professional-pdf-adapter@1.0.0" in protocol


def test_production_core_contains_no_field_acceptance_company_special_cases():
    forbidden = ("300034", "001287", "301073", "钢研高纳", "中电港", "君亭酒店")
    offenders: list[tuple[str, str]] = []
    for path in Path("src/research_os").rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        for value in forbidden:
            if value in content:
                offenders.append((str(path), value))

    assert offenders == []
