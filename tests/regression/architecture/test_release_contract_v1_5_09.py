from __future__ import annotations

import json
from pathlib import Path

import research_os
from research_os.presentation import PlaywrightPdfAdapter, ProfessionalHtmlRenderer
from research_os.release.replays import REPLAY_REGISTRY
from research_os.release.runtime import CHECKS
from research_os.reporting.composer_v1_5_09 import ResearchReportComposer
from research_os.reporting.markdown_renderer_v1_5_09 import ResearchReportMarkdownRenderer
from research_os.reporting.research_view_v1_5_09 import ResearchViewPresenter
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


V1_5_09_CHECKS = {
    "financial_fact_snapshot_v1_5_09": (
        "tests/unit/runtime/test_financial_fact_snapshot_v1_5_09.py"
    ),
    "research_depth_semantics_v1_5_09": (
        "tests/unit/reporting/test_research_depth_semantics_v1_5_09.py"
    ),
    "professional_output_depth_v1_5_09": (
        "tests/unit/reporting/test_professional_output_depth_v1_5_09.py"
    ),
    "dual_field_acceptance_v1_5_09": (
        "tests/integration/presentation/test_field_acceptance_v1_5_09.py"
    ),
    "three_company_field_depth_v1_5_09": (
        "tests/regression/research_patterns/test_v1_5_09_field_depth_patterns.py"
    ),
    "release_contract_v1_5_09": (
        "tests/regression/architecture/test_release_contract_v1_5_09.py"
    ),
}


def _version(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("."))


def test_v1_5_09_depth_fingerprints_remain_replayable():
    metadata = json.loads(Path("research_os_version.json").read_text(encoding="utf-8"))

    current = RESEARCH_OS_VERSION
    assert _version(current) >= _version("1.5.9")
    assert research_os.__version__ == current
    assert metadata["research_os_version"] == current
    assert metadata["status"] == "stable"
    assert CORE_API_VERSION == "1.0"
    assert metadata["core_api_version"] == "1.0"

    modules = metadata["module_versions"]
    assert _version(modules["semantic_research_view"]) >= _version("1.4.0")
    assert _version(modules["report_composer"]) >= _version("1.2.0")
    assert _version(modules["markdown_renderer"]) >= _version("1.1.0")
    assert _version(modules["financial_fact_snapshot"]) >= _version("1.0.0")
    assert _version(modules["html_renderer"]) >= _version("1.0.0")
    assert _version(modules["pdf_adapter"]) >= _version("1.0.0")

    assert ResearchViewPresenter.version == "professional-research-view@1.4.0"
    assert ResearchReportComposer.version == "research-report-composer@1.2.0"
    assert ResearchReportMarkdownRenderer.version == "professional-markdown-renderer@1.1.0"
    assert ProfessionalHtmlRenderer.version == "professional-html-renderer@1.0.0"
    assert PlaywrightPdfAdapter.version == "professional-pdf-adapter@1.0.0"


def test_release_gate_requires_v1_5_09_depth_checks_without_removing_prior_gates():
    for gate, nodeid in V1_5_09_CHECKS.items():
        assert CHECKS.get(gate) == nodeid
        assert Path(nodeid.split("::", 1)[0]).exists()

    for prior_gate in (
        "report_composer_one_way",
        "composition_coverage_v1_5_06",
        "markdown_renderer_v1_5_07",
        "presentation_artifacts_v1_5_08",
        "field_acceptance_v1_5_08",
    ):
        assert prior_gate in CHECKS


def test_v1_5_09_field_acceptance_is_a_frozen_replay_profile():
    profile = REPLAY_REGISTRY["field-v1.5.09"]
    assert profile.frozen is True
    assert profile.runner_script == "scripts/render_field_acceptance_v1_5_09.py"
    assert profile.fixture_dir == "tests/fixtures/field_acceptance/v1_5_09"
    assert Path(profile.runner_script).exists()
    assert Path(profile.fixture_dir).exists()


def test_v1_5_09_documentation_records_depth_gate_and_one_way_boundary():
    migration = Path("docs/migrations/v1.5.09.md")
    readme = Path("README.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    protocol = Path("docs/prompts/stock_research.md").read_text(encoding="utf-8")

    assert migration.exists()
    migration_text = migration.read_text(encoding="utf-8")
    for text in (
        "FinancialFactSnapshot",
        "professional-research-view@1.4.0",
        "research-report-composer@1.2.0",
        "professional-markdown-renderer@1.1.0",
        "presentation",
        "research_depth",
        "不重新计算",
        "无数据库迁移",
        "Hospitality Plugin",
    ):
        assert text in migration_text

    assert "Research OS v1.5.09" in readme
    assert "## 1.5.9" in changelog
    assert "professional-research-view@1.4.0" in protocol
    assert "research-report-composer@1.2.0" in protocol
    assert "professional-markdown-renderer@1.1.0" in protocol
    assert "research_depth" in protocol


def test_v1_5_09_adds_no_database_migration_and_no_hospitality_strategy_plugin():
    revisions = sorted(path.name for path in Path("alembic/versions").glob("*.py"))
    assert revisions == [
        "0001_evidence.py",
        "0002_v1_1_semantics.py",
        "0003_v1_2_evidence_lineage.py",
    ]

    builtins = Path("src/research_os/plugins/builtins.py").read_text(encoding="utf-8")
    assert "industry:hospitality" not in builtins
    assert "HospitalityPlugin" not in builtins


def test_v1_5_09_production_core_has_no_three_company_special_cases():
    forbidden = ("300034", "001287", "301073", "钢研高纳", "中电港", "君亭酒店")
    offenders = []
    for path in Path("src/research_os").rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        for value in forbidden:
            if value in content:
                offenders.append((str(path), value))

    assert offenders == []
