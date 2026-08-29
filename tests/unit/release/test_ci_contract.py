from pathlib import Path

from research_os.release.gate import REQUIRED
from research_os.release.runtime import CHECKS


def test_release_gate_includes_reversible_v1_2_migration_check():
    assert "migration_lineage" in REQUIRED
    assert CHECKS["migration_lineage"] == "tests/integration/storage/test_v1_2_lineage_migration.py"


def test_ci_explicitly_runs_migration_smoke_before_full_suite():
    workflow = Path(".github/workflows/ci.yml").read_text()
    assert "test_v1_2_lineage_migration.py" in workflow
    assert "pytest -q" in workflow
    assert "python scripts/release_gate_v1_1.py" in workflow
