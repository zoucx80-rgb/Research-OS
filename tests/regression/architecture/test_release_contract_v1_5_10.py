from __future__ import annotations

import json
from pathlib import Path

import research_os
from research_os.presentation import PlaywrightPdfAdapter, ProfessionalHtmlRenderer
from research_os.release.replays import REPLAY_REGISTRY
from research_os.release.runtime import CHECKS
from research_os.reporting.composer_v1_5_10 import ResearchReportComposer
from research_os.reporting.markdown_renderer_v1_5_10 import ResearchReportMarkdownRenderer
from research_os.reporting.research_view_v1_5_10 import ResearchViewPresenter
from research_os.runtime.research_completeness import ResearchCompletenessModule
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


V1_5_10_CHECKS = {
    "research_completeness_contracts_v1_5_10": (
        "tests/unit/completeness/test_models_and_services.py"
    ),
    "research_completeness_runtime_v1_5_10": (
        "tests/unit/runtime/test_research_completeness_v1_5_10.py"
    ),
    "research_completeness_reporting_v1_5_10": (
        "tests/unit/reporting/test_research_completeness_v1_5_10.py"
    ),
    "research_completeness_field_v1_5_10": (
        "tests/integration/presentation/test_field_acceptance_v1_5_10.py"
    ),
    "research_completeness_patterns_v1_5_10": (
        "tests/regression/research_patterns/test_v1_5_10_research_completeness.py"
    ),
    "release_contract_v1_5_10": (
        "tests/regression/architecture/test_release_contract_v1_5_10.py"
    ),
}


def test_v1_5_10_versions_and_component_fingerprints_remain_replayable():
    metadata = json.loads(Path("research_os_version.json").read_text(encoding="utf-8"))

    assert tuple(map(int, RESEARCH_OS_VERSION.split("."))) >= (1, 5, 10)
    assert research_os.__version__ == RESEARCH_OS_VERSION
    assert metadata["research_os_version"] == RESEARCH_OS_VERSION
    assert metadata["status"] == "stable"
    assert CORE_API_VERSION == "1.0"
    assert metadata["core_api_version"] == "1.0"

    modules = metadata["module_versions"]
    assert modules["research_completeness"] == "1.0.0"
    assert tuple(map(int, modules["semantic_research_view"].split("."))) >= (1, 5, 0)
    assert modules["report_composer"] == "1.3.0"
    assert tuple(map(int, modules["markdown_renderer"].split("."))) >= (1, 2, 0)
    assert modules["financial_fact_snapshot"] == "1.0.0"
    assert modules["html_renderer"] == "1.0.0"
    assert modules["pdf_adapter"] == "1.0.0"

    assert ResearchCompletenessModule.spec.module_id == "research_completeness"
    assert ResearchCompletenessModule.spec.module_version == "1.0.0"
    assert ResearchViewPresenter.version == "professional-research-view@1.5.0"
    assert ResearchReportComposer.version == "research-report-composer@1.3.0"
    assert ResearchReportMarkdownRenderer.version == "professional-markdown-renderer@1.2.0"
    assert ProfessionalHtmlRenderer.version == "professional-html-renderer@1.0.0"
    assert PlaywrightPdfAdapter.version == "professional-pdf-adapter@1.0.0"


def test_release_gate_requires_v1_5_10_checks_without_removing_prior_gates():
    for gate, nodeid in V1_5_10_CHECKS.items():
        assert CHECKS.get(gate) == nodeid
        assert Path(nodeid.split("::", 1)[0]).exists()

    for prior_gate in (
        "report_composer_one_way",
        "composition_coverage_v1_5_06",
        "markdown_renderer_v1_5_07",
        "presentation_artifacts_v1_5_08",
        "field_acceptance_v1_5_08",
        "financial_fact_snapshot_v1_5_09",
        "dual_field_acceptance_v1_5_09",
        "release_contract_v1_5_09",
    ):
        assert prior_gate in CHECKS


def test_v1_5_10_field_acceptance_is_a_frozen_replay_profile():
    profile = REPLAY_REGISTRY["field-v1.5.10"]
    assert profile.frozen is True
    assert profile.runner_script == "scripts/render_field_acceptance_v1_5_10.py"
    assert profile.fixture_dir == "tests/fixtures/field_acceptance/v1_5_10"
    assert Path(profile.runner_script).exists()
    assert Path(profile.fixture_dir).exists()


def test_v1_5_10_documentation_records_completeness_gate_and_one_way_boundary():
    migration = Path("docs/migrations/v1.5.10.md")
    readme = Path("README.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    protocol = Path("docs/prompts/stock_research.md").read_text(encoding="utf-8")

    assert migration.exists()
    migration_text = migration.read_text(encoding="utf-8")
    for text in (
        "research_completeness@1.0.0",
        "professional-research-view@1.5.0",
        "research-report-composer@1.3.0",
        "professional-markdown-renderer@1.2.0",
        "PASS",
        "INCOMPLETE",
        "NOT_APPLICABLE",
        "不重新计算",
        "无数据库迁移",
        "Hospitality Plugin",
    ):
        assert text in migration_text

    assert "Research OS v1.5.10" in readme
    assert "research_completeness" in readme
    assert "## 1.5.10" in changelog
    assert "professional-research-view@1.5.0" in protocol
    assert "research-report-composer@1.3.0" in protocol
    assert "professional-markdown-renderer@1.2.0" in protocol
    assert "research_completeness" in protocol
    assert "NOT_APPLICABLE" in protocol


def test_v1_5_10_adds_no_database_migration_and_no_hospitality_strategy_plugin():
    revisions = sorted(path.name for path in Path("alembic/versions").glob("*.py"))
    assert revisions == [
        "0001_evidence.py",
        "0002_v1_1_semantics.py",
        "0003_v1_2_evidence_lineage.py",
    ]

    builtins = Path("src/research_os/plugins/builtins.py").read_text(encoding="utf-8")
    assert "industry:hospitality" not in builtins
    assert "HospitalityPlugin" not in builtins


def test_v1_5_10_production_core_and_generic_fixture_have_no_validation_company_special_cases():
    forbidden = ("300034", "001287", "301073", "钢研高纳", "中电港", "君亭酒店")
    offenders = []
    for path in Path("src/research_os").rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        for value in forbidden:
            if value in content:
                offenders.append((str(path), value))

    fixture = Path(
        "tests/fixtures/field_acceptance/v1_5_10/manufacturing_completeness.json"
    ).read_text(encoding="utf-8")
    for value in forbidden:
        if value in fixture:
            offenders.append(("manufacturing_completeness.json", value))

    assert offenders == []
