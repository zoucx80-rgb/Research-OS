from __future__ import annotations

import os
import sqlite3
import subprocess

from sqlalchemy import create_engine, inspect, text


def _alembic(db_path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{db_path}"
    return subprocess.run(
        ["alembic", "-c", "alembic.ini", *arguments],
        capture_output=True,
        text=True,
        env=environment,
    )


def test_v1_6_upgrade_preserves_legacy_evidence_and_upgrades_snapshot_contract(
    tmp_path,
) -> None:
    database = tmp_path / "research.sqlite3"
    legacy = _alembic(database, "upgrade", "0003_v1_2_evidence_lineage")
    assert legacy.returncode == 0, legacy.stderr

    connection = sqlite3.connect(database)
    connection.execute(
        """
        INSERT INTO evidence (
            evidence_id, revision_no, company_id, evidence_type, publish_ts,
            ingested_at, value_json, confidence_grade, verification_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "legacy-evidence",
            1,
            "000001.SZ",
            "filing_fact",
            "2026-01-01 00:00:00.000000",
            "2026-01-01 00:00:00.000000",
            '{"reported": true}',
            "A",
            "PRIMARY_VERIFIED",
        ),
    )
    connection.execute(
        """
        INSERT INTO research_snapshot (
            snapshot_id, company_id, decision_ts, versions_json, payload_json, payload_hash
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("legacy-snapshot", "000001.SZ", "2026-01-01 00:00:00.000000", "{}", "{}", "legacy-hash"),
    )
    connection.commit()
    connection.close()

    upgraded = _alembic(database, "upgrade", "head")
    assert upgraded.returncode == 0, upgraded.stderr

    engine = create_engine(f"sqlite:///{database}")
    inspector = inspect(engine)
    assert {"research_run", "research_snapshot", "artifact_index"} <= set(
        inspector.get_table_names()
    )
    evidence_columns = {column["name"] for column in inspector.get_columns("evidence")}
    assert {
        "comparison_basis",
        "metric_kind",
        "lineage_json",
        "content_hash",
    } <= evidence_columns
    snapshot_columns = {
        column["name"] for column in inspector.get_columns("research_snapshot")
    }
    assert {
        "schema_version",
        "codec_version",
        "hash_algorithm",
        "run_id",
        "created_at",
        "baseline_json",
        "component_fingerprints_json",
        "artifact_fingerprints_json",
        "research_digest",
        "integrity_digest",
    } <= snapshot_columns
    snapshot_unique_columns = {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("research_snapshot")
    }
    snapshot_foreign_keys = {
        (
            tuple(constraint["constrained_columns"]),
            constraint["referred_table"],
            tuple(constraint["referred_columns"]),
        )
        for constraint in inspector.get_foreign_keys("research_snapshot")
    }
    assert ("run_id",) in snapshot_unique_columns
    assert (("run_id",), "research_run", ("run_id",)) in snapshot_foreign_keys

    with engine.connect() as connection:
        evidence = connection.execute(
            text(
                "SELECT value_json, raw_value_json, normalized_value_json, content_hash "
                "FROM evidence WHERE evidence_id = 'legacy-evidence'"
            )
        ).one()
        snapshot = connection.execute(
            text(
                "SELECT payload_hash, schema_version FROM research_snapshot "
                "WHERE snapshot_id = 'legacy-snapshot'"
            )
        ).one()
    assert evidence == ('{"reported": true}', None, None, None)
    assert snapshot == ("legacy-hash", None)


def test_v1_6_downgrade_only_removes_v1_6_additions(tmp_path) -> None:
    database = tmp_path / "research.sqlite3"
    upgraded = _alembic(database, "upgrade", "head")
    assert upgraded.returncode == 0, upgraded.stderr

    downgraded = _alembic(database, "downgrade", "0003_v1_2_evidence_lineage")
    assert downgraded.returncode == 0, downgraded.stderr

    inspector = inspect(create_engine(f"sqlite:///{database}"))
    tables = set(inspector.get_table_names())
    assert "evidence" in tables
    assert "research_snapshot" in tables
    assert not {"research_run", "artifact_index"} & tables
    evidence_columns = {column["name"] for column in inspector.get_columns("evidence")}
    assert not {"comparison_basis", "metric_kind", "lineage_json", "content_hash"} & evidence_columns
