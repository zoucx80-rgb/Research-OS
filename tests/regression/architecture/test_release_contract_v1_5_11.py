from __future__ import annotations

from pathlib import Path

from research_os.presentation import PlaywrightPdfAdapter, ProfessionalHtmlRenderer
from research_os.release.manifest import CURRENT_RELEASE
from research_os.release.replays import REPLAY_REGISTRY
from research_os.release.verification import PACK_REGISTRY, resolve_release_checks
from research_os.reporting import ResearchReportComposer
from research_os.reporting.markdown_renderer_v1_5_11 import ResearchReportMarkdownRenderer
from research_os.reporting.research_view_v1_5_11 import ResearchViewPresenter
from research_os.runtime.professional_modules import ProfessionalDriverThesisModule


V1_5_11_CHECKS = {
    "semantic_signal_contract_v1_5_11": "tests/unit/thesis/test_semantic_signals_v1_5_11.py",
    "thesis_lifecycle_v1_5_11": "tests/unit/thesis/test_lifecycle_semantics_v1_5_11.py",
    "expectation_missingness_v1_5_11": "tests/unit/decision/test_missing_expectation_v1_5_11.py",
    "semantic_runtime_v1_5_11": "tests/integration/runtime/test_semantic_thesis_runtime_v1_5_11.py",
    "presentation_integrity_v1_5_11": "tests/unit/reporting/test_semantic_integrity_v1_5_11.py",
    "semantic_output_patterns_v1_5_11": "tests/regression/research_patterns/test_v1_5_11_semantic_output_patterns.py",
    "semantic_correctness_patterns_v1_5_11": "tests/regression/research_patterns/test_v1_5_11_semantic_correctness.py",
    "semantic_architecture_v1_5_11": "tests/regression/architecture/test_semantic_correctness_contract_v1_5_11.py",
    "semantic_field_v1_5_11": "tests/integration/presentation/test_field_acceptance_v1_5_11.py",
    "release_contract_v1_5_11": "tests/regression/architecture/test_release_contract_v1_5_11.py",
}


def test_v1_5_11_component_fingerprints_match_current_manifest():
    assert CURRENT_RELEASE.version == "1.5.11"
    assert CURRENT_RELEASE.status == "stable"
    assert CURRENT_RELEASE.core_api_version == "1.0"

    modules = CURRENT_RELEASE.module_versions
    assert modules["driver_engine"] == "1.4.0"
    assert modules["semantic_research_view"] == "1.6.0"
    assert modules["report_composer"] == "1.3.0"
    assert modules["markdown_renderer"] == "1.3.0"
    assert modules["html_renderer"] == "1.0.0"
    assert modules["pdf_adapter"] == "1.0.0"

    assert ProfessionalDriverThesisModule.spec.module_version == "1.4.0"
    assert ResearchViewPresenter.version == "professional-research-view@1.6.0"
    assert ResearchReportComposer.version == "research-report-composer@1.3.0"
    assert ResearchReportMarkdownRenderer.version == "professional-markdown-renderer@1.3.0"
    assert ProfessionalHtmlRenderer.version == "professional-html-renderer@1.0.0"
    assert PlaywrightPdfAdapter.version == "professional-pdf-adapter@1.0.0"


def test_semantic_correctness_pack_resolves_all_v1_5_11_checks():
    pack = PACK_REGISTRY["semantic-correctness"]
    assert set(pack.check_ids) == set(V1_5_11_CHECKS)

    resolved = resolve_release_checks(CURRENT_RELEASE)
    for gate, nodeid in V1_5_11_CHECKS.items():
        assert resolved.get(gate) == nodeid
        assert Path(nodeid.split("::", 1)[0]).exists()

    for prior_gate in (
        "field_acceptance_v1_5_08",
        "dual_field_acceptance_v1_5_09",
        "release_contract_v1_5_09",
        "research_completeness_field_v1_5_10",
        "release_contract_v1_5_10",
    ):
        assert prior_gate in resolved


def test_v1_5_11_field_acceptance_is_the_current_replay_profile():
    profile = REPLAY_REGISTRY["field-v1.5.11"]
    assert profile.frozen is False
    assert profile.runner_script == "scripts/render_field_acceptance_v1_5_11.py"
    assert profile.fixture_dir == "tests/fixtures/field_acceptance/v1_5_11"
    assert Path(profile.runner_script).exists()
    assert Path(profile.fixture_dir).exists()


def test_v1_5_11_documentation_records_semantic_safety_and_one_way_boundary():
    migration = Path("docs/migrations/v1.5.11.md")
    readme = Path("README.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    protocol = Path("docs/prompts/stock_research.md").read_text(encoding="utf-8")

    assert migration.exists()
    migration_text = migration.read_text(encoding="utf-8")
    for text in (
        "professional-research-view@1.6.0",
        "professional-markdown-renderer@1.3.0",
        "UNRESOLVED",
        "UNKNOWN",
        "NOT_COMPARABLE",
        "不重新计算",
        "无数据库迁移",
    ):
        assert text in migration_text

    assert "Research OS v1.5.11" in readme
    assert "comparison" in readme.lower() or "比较口径" in readme
    assert "## 1.5.11" in changelog
    assert "professional-research-view@1.6.0" in protocol
    assert "professional-markdown-renderer@1.3.0" in protocol
    assert "UNRESOLVED" in protocol
    assert "UNKNOWN" in protocol


def test_v1_5_11_adds_no_database_migration_or_company_specific_production_logic():
    revisions = sorted(path.name for path in Path("alembic/versions").glob("*.py"))
    assert revisions == [
        "0001_evidence.py",
        "0002_v1_1_semantics.py",
        "0003_v1_2_evidence_lineage.py",
    ]

    forbidden = ("300034", "001287", "301073", "钢研高纳", "中电港", "君亭酒店")
    offenders = []
    for path in Path("src/research_os").rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        for value in forbidden:
            if value in content:
                offenders.append((str(path), value))
    assert offenders == []
