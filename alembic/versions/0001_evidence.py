"""create evidence table"""
from alembic import op
import sqlalchemy as sa
revision='0001_evidence'; down_revision=None; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('evidence',
      sa.Column('id',sa.Integer(),primary_key=True),sa.Column('evidence_id',sa.String(),nullable=False),sa.Column('revision_no',sa.Integer(),nullable=False,server_default='1'),
      sa.Column('company_id',sa.String(),nullable=False),sa.Column('evidence_type',sa.String(),nullable=False),sa.Column('period_end',sa.Date(),nullable=True),
      sa.Column('publish_ts',sa.DateTime(timezone=True),nullable=False),sa.Column('ingested_at',sa.DateTime(timezone=True),nullable=False),sa.Column('value_json',sa.Text(),nullable=True),
      sa.Column('unit',sa.String(),nullable=True),sa.Column('scope',sa.String(),nullable=True),sa.Column('source_document_id',sa.String(),nullable=True),sa.Column('source_page',sa.Integer(),nullable=True),
      sa.Column('source_table',sa.String(),nullable=True),sa.Column('source_url',sa.Text(),nullable=True),sa.Column('confidence_grade',sa.String(),nullable=False),sa.Column('verification_status',sa.String(),nullable=False),
      sa.Column('dataset_version',sa.String(),nullable=True),sa.Column('parser_version',sa.String(),nullable=True),sa.Column('formula_version',sa.String(),nullable=True),sa.Column('model_version',sa.String(),nullable=True),
      sa.UniqueConstraint('evidence_id','revision_no',name='uq_evidence_revision'))
    op.create_index('ix_evidence_company_id','evidence',['company_id'])
    op.create_index('ix_evidence_publish_ts','evidence',['publish_ts'])

def downgrade(): op.drop_table('evidence')
