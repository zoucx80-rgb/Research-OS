from pathlib import Path

from research_os.release.gate import REQUIRED
from research_os.release.runtime import CHECKS


V1_2_1_CHECKS = {
    "period_semantics": "tests/unit/kpi/test_period_sensitive_packs.py",
    "missing_value_semantics": "tests/unit/capital/test_engine.py::test_negative_ocf_without_funding_inputs_does_not_invent_funding_state",
    "kpi_applicability": "tests/unit/kpi/test_applicability.py",
    "completion_consistency": "tests/unit/completion/test_consistency.py",
    "version_consistency": "tests/unit/test_version_consistency_v1_2_1.py",
}


def test_release_gate_includes_reversible_v1_2_migration_check():
    assert "migration_lineage" in REQUIRED
    assert CHECKS["migration_lineage"] == "tests/integration/storage/test_v1_2_lineage_migration.py"


def test_release_gate_registers_all_v1_2_1_correctness_checks():
    for name, nodeid in V1_2_1_CHECKS.items():
        assert name in REQUIRED
        assert CHECKS[name] == nodeid


def test_ci_runs_v1_2_1_semantics_before_migration_and_full_suite():
    workflow = Path(".github/workflows/ci.yml").read_text()
    targeted = "tests/regression/research_patterns/test_v1_2_1_correctness_patterns.py"
    migration = "test_v1_2_lineage_migration.py"
    release_gate = "python scripts/release_gate_v1_1.py"
    assert targeted in workflow
    assert migration in workflow
    assert release_gate in workflow
    assert workflow.index(targeted) < workflow.index(migration) < workflow.index(release_gate)
