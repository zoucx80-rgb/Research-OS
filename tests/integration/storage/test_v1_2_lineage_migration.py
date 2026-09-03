import os
import subprocess

from sqlalchemy import create_engine, inspect


def _run_alembic(db, *args):
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db}"
    return subprocess.run(
        ["alembic", "-c", "alembic.ini", *args], capture_output=True, text=True, env=env
    )


def test_v1_2_migration_adds_evidence_lineage_columns_and_is_reversible(tmp_path):
    db = tmp_path / "research.sqlite3"
    up = _run_alembic(db, "upgrade", "head")
    assert up.returncode == 0, up.stderr
    inspector = inspect(create_engine(f"sqlite:///{db}"))
    columns = {column["name"] for column in inspector.get_columns("evidence")}
    assert {"raw_value_json", "normalized_value_json", "period", "version"} <= columns

    down = _run_alembic(db, "downgrade", "0002_v1_1_semantics")
    assert down.returncode == 0, down.stderr
    inspector = inspect(create_engine(f"sqlite:///{db}"))
    columns = {column["name"] for column in inspector.get_columns("evidence")}
    assert not ({"raw_value_json", "normalized_value_json", "period", "version"} & columns)

    up_again = _run_alembic(db, "upgrade", "head")
    assert up_again.returncode == 0, up_again.stderr
