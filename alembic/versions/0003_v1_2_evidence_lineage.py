"""persist Evidence raw/normalized lineage fields for Research OS v1.2"""
from alembic import op
import sqlalchemy as sa

revision = "0003_v1_2_evidence_lineage"
down_revision = "0002_v1_1_semantics"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("evidence") as batch:
        batch.add_column(sa.Column("period", sa.String(), nullable=True))
        batch.add_column(sa.Column("raw_value_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("normalized_value_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("version", sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table("evidence") as batch:
        batch.drop_column("version")
        batch.drop_column("normalized_value_json")
        batch.drop_column("raw_value_json")
        batch.drop_column("period")
