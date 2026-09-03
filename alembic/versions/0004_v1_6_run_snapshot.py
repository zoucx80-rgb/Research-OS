"""add Research OS v1.6 run, snapshot, and evidence persistence contracts

Revision ID: 0004_v1_6_run_snapshot
Revises: 0003_v1_2_evidence_lineage
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_v1_6_run_snapshot"
down_revision = "0003_v1_2_evidence_lineage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_run",
        sa.Column("run_id", sa.String(), primary_key=True),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("decision_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("baseline_json", sa.Text(), nullable=False),
        sa.Column("versions_json", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_research_run_company_decision",
        "research_run",
        ["company_id", "decision_ts"],
    )
    # The v1.1 table remains the same physical table. Legacy snapshots do not
    # become v2 snapshots merely by receiving nullable metadata columns.
    with op.batch_alter_table("research_snapshot") as batch:
        batch.add_column(sa.Column("schema_version", sa.String(), nullable=True))
        batch.add_column(sa.Column("codec_version", sa.String(), nullable=True))
        batch.add_column(sa.Column("hash_algorithm", sa.String(), nullable=True))
        batch.add_column(
            sa.Column(
                "run_id",
                sa.String(),
                sa.ForeignKey("research_run.run_id", name="fk_research_snapshot_run"),
                nullable=True,
            )
        )
        batch.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("baseline_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("component_fingerprints_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("artifact_fingerprints_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("research_digest", sa.String(), nullable=True))
        batch.add_column(sa.Column("integrity_digest", sa.String(), nullable=True))
        batch.create_unique_constraint("uq_research_snapshot_run_id", ["run_id"])

    with op.batch_alter_table("evidence") as batch:
        batch.add_column(sa.Column("comparison_basis", sa.String(), nullable=True))
        batch.add_column(sa.Column("metric_kind", sa.String(), nullable=True))
        batch.add_column(sa.Column("lineage_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("content_hash", sa.String(), nullable=True))

    op.create_index("ix_evidence_company_publish", "evidence", ["company_id", "publish_ts"])
    op.create_index(
        "ix_evidence_company_id_publish_revision",
        "evidence",
        ["company_id", "evidence_id", "publish_ts", "revision_no"],
    )
    op.create_index(
        "ix_research_snapshot_company_decision",
        "research_snapshot",
        ["company_id", "decision_ts"],
    )

    op.create_table(
        "artifact_index",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("snapshot_id", sa.String(), nullable=False),
        sa.Column("artifact_id", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["research_snapshot.snapshot_id"]),
        sa.UniqueConstraint(
            "snapshot_id",
            "artifact_id",
            "schema_version",
            "provider_id",
            name="uq_artifact_index_snapshot_key_provider",
        ),
    )
    op.create_index("ix_artifact_index_snapshot", "artifact_index", ["snapshot_id"])


def downgrade() -> None:
    op.drop_index("ix_artifact_index_snapshot", table_name="artifact_index")
    op.drop_table("artifact_index")
    op.drop_index("ix_research_snapshot_company_decision", table_name="research_snapshot")
    op.drop_index("ix_evidence_company_id_publish_revision", table_name="evidence")
    op.drop_index("ix_evidence_company_publish", table_name="evidence")
    with op.batch_alter_table("evidence") as batch:
        batch.drop_column("content_hash")
        batch.drop_column("lineage_json")
        batch.drop_column("metric_kind")
        batch.drop_column("comparison_basis")
    with op.batch_alter_table("research_snapshot") as batch:
        batch.drop_constraint("uq_research_snapshot_run_id", type_="unique")
        batch.drop_column("integrity_digest")
        batch.drop_column("research_digest")
        batch.drop_column("artifact_fingerprints_json")
        batch.drop_column("component_fingerprints_json")
        batch.drop_column("baseline_json")
        batch.drop_column("created_at")
        batch.drop_column("run_id")
        batch.drop_column("hash_algorithm")
        batch.drop_column("codec_version")
        batch.drop_column("schema_version")
    op.drop_index("ix_research_run_company_decision", table_name="research_run")
    op.drop_table("research_run")
