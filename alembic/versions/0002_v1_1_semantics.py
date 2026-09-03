"""create Research OS v1.1 semantic, analytics, monitoring and governance tables"""

from alembic import op
import sqlalchemy as sa

revision = "0002_v1_1_semantics"
down_revision = "0001_evidence"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "research_snapshot",
        sa.Column("snapshot_id", sa.String(), primary_key=True),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("decision_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("versions_json", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("payload_hash", sa.String(), nullable=False, server_default=""),
    )

    op.create_table(
        "core_business_model_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("primary_model", sa.String(), nullable=False),
        sa.Column("secondary_models_json", sa.Text()),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False),
        sa.Column("router_version", sa.String(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "core_kpi_pack_registry",
        sa.Column("pack_id", sa.String(), primary_key=True),
        sa.Column("pack_version", sa.String(), nullable=False),
        sa.Column("eligible_models_json", sa.Text(), nullable=False),
        sa.Column("required_facts_json", sa.Text(), nullable=False),
        sa.Column("optional_facts_json", sa.Text(), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "core_driver_node",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("driver_id", sa.String(), nullable=False),
        sa.Column("driver_type", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "core_driver_edge",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("from_driver", sa.String(), nullable=False),
        sa.Column("to_driver", sa.String(), nullable=False),
        sa.Column("relation", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )

    op.create_table(
        "research_thesis",
        sa.Column("thesis_id", sa.String(), primary_key=True),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "research_falsifier",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("thesis_id", sa.String(), nullable=False),
        sa.Column("metric", sa.String(), nullable=False),
        sa.Column("operator", sa.String(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "research_claim",
        sa.Column("claim_id", sa.String(), primary_key=True),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("confidence_grade", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "research_evidence_link",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("claim_id", sa.String(), nullable=False),
        sa.Column("evidence_id", sa.String(), nullable=False),
        sa.Column("relation", sa.String(), nullable=False, server_default="supports"),
    )

    op.create_table(
        "pit_consensus_vintage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("forecast_period", sa.String(), nullable=False),
        sa.Column("expectation_type", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "pit_expectation_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("decision_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )

    for table in [
        "analytics_capital_efficiency",
        "analytics_funding_loop",
        "analytics_model_fitness",
        "analytics_decision_state",
        "analytics_forecast_error",
    ]:
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.String(), nullable=False),
            sa.Column("decision_ts", sa.DateTime(timezone=True), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
        )

    op.create_table(
        "monitoring_thesis_transition",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("thesis_id", sa.String(), nullable=False),
        sa.Column("from_status", sa.String()),
        sa.Column("to_status", sa.String(), nullable=False),
        sa.Column("transition_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "monitoring_model_drift",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("detected_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "monitoring_research_postmortem",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )

    op.create_table(
        "governance_os_version",
        sa.Column("version", sa.String(), primary_key=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "governance_module_version",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("module_name", sa.String(), nullable=False),
        sa.Column("module_version", sa.String(), nullable=False),
        sa.Column("os_version", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "governance_migration",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("from_version", sa.String(), nullable=False),
        sa.Column("to_version", sa.String(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )


def downgrade():
    for name in [
        "governance_migration",
        "governance_module_version",
        "governance_os_version",
        "monitoring_research_postmortem",
        "monitoring_model_drift",
        "monitoring_thesis_transition",
        "analytics_forecast_error",
        "analytics_decision_state",
        "analytics_model_fitness",
        "analytics_funding_loop",
        "analytics_capital_efficiency",
        "pit_expectation_snapshot",
        "pit_consensus_vintage",
        "research_evidence_link",
        "research_claim",
        "research_falsifier",
        "research_thesis",
        "core_driver_edge",
        "core_driver_node",
        "core_kpi_pack_registry",
        "core_business_model_profile",
        "research_snapshot",
    ]:
        op.drop_table(name)
