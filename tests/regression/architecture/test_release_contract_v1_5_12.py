from pathlib import Path

from research_os.release.manifest import CURRENT_RELEASE
from research_os.release.replays import REPLAY_REGISTRY
from research_os.release.verification import PACK_REGISTRY, resolve_release_checks
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


V1_5_12_CHECKS = {
    "claim_strength_contract_v1_5_12": "tests/unit/semantics/test_claims.py",
    "semantic_context_contract_v1_5_12": "tests/unit/completeness/test_semantic_context_v1_5_12.py",
    "semantic_preservation_runtime_v1_5_12": "tests/integration/runtime/test_semantic_preservation_v1_5_12.py",
    "valuation_reconciliation_v1_5_12": "tests/unit/valuation/test_reconciliation_v1_5_12.py",
    "valuation_reconciliation_runtime_v1_5_12": "tests/integration/runtime/test_valuation_reconciliation_v1_5_12.py",
    "semantic_preservation_reporting_v1_5_12": "tests/unit/reporting/test_semantic_preservation_v1_5_12.py",
    "semantic_preservation_architecture_v1_5_12": "tests/regression/architecture/test_semantic_preservation_contract_v1_5_12.py",
    "semantic_preservation_field_v1_5_12": "tests/integration/presentation/test_field_acceptance_v1_5_12.py",
    "release_contract_v1_5_12": "tests/regression/architecture/test_release_contract_v1_5_12.py",
}


def test_v1_5_12_release_identity_and_component_fingerprints():
    assert RESEARCH_OS_VERSION == CURRENT_RELEASE.version == "1.5.12"
    assert CORE_API_VERSION == CURRENT_RELEASE.core_api_version == "1.0"
    assert CURRENT_RELEASE.status == "stable"

    modules = CURRENT_RELEASE.module_versions
    assert modules["semantic_research_view"] == "1.7.0"
    assert modules["semantic_preservation"] == "1.0.0"
    assert modules["semantic_claims"] == "1.0.0"
    assert modules["valuation_reconciliation"] == "1.0.0"
    assert modules["report_composer"] == "1.4.0"
    assert modules["markdown_renderer"] == "1.4.0"


def test_semantic_preservation_pack_resolves_all_v1_5_12_checks():
    pack = PACK_REGISTRY["semantic-preservation"]
    assert set(pack.check_ids) == set(V1_5_12_CHECKS)
    resolved = resolve_release_checks(CURRENT_RELEASE)
    for gate, nodeid in V1_5_12_CHECKS.items():
        assert resolved.get(gate) == nodeid
        assert Path(nodeid).exists()


def test_v1_5_11_is_frozen_and_v1_5_12_is_current_field_profile():
    previous = REPLAY_REGISTRY["field-v1.5.11"]
    current = REPLAY_REGISTRY["field-v1.5.12"]
    assert previous.frozen is True
    assert current.frozen is False
    assert current.runner_script == "scripts/render_field_acceptance_v1_5_12.py"
    assert current.fixture_dir == "tests/fixtures/field_acceptance/v1_5_12"


def test_v1_5_12_documentation_and_migration_contract():
    migration = Path("docs/migrations/v1.5.12.md")
    assert migration.exists()
    text = migration.read_text(encoding="utf-8")
    for value in (
        "professional-research-view@1.7.0",
        "research-report-composer@1.4.0",
        "professional-markdown-renderer@1.4.0",
        "CORE_API_VERSION",
        "1.0",
        "无数据库迁移",
    ):
        assert value in text

    assert "# Research OS v1.5.12" in Path("README.md").read_text(encoding="utf-8")
    assert "## 1.5.12" in Path("CHANGELOG.md").read_text(encoding="utf-8")
