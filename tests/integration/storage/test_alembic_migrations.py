import os, subprocess
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_creates_v1_1_core_tables(tmp_path):
    db=tmp_path/'research.sqlite3'
    env=os.environ.copy(); env['DATABASE_URL']=f'sqlite:///{db}'
    p=subprocess.run(['alembic','-c','alembic.ini','upgrade','head'],capture_output=True,text=True,env=env)
    assert p.returncode==0, p.stderr
    tables=set(inspect(create_engine(f'sqlite:///{db}')).get_table_names())
    required={
      'evidence','research_snapshot',
      'core_business_model_profile','core_kpi_pack_registry','core_driver_node','core_driver_edge',
      'research_thesis','research_falsifier','research_claim','research_evidence_link',
      'pit_consensus_vintage','pit_expectation_snapshot',
      'analytics_capital_efficiency','analytics_funding_loop','analytics_model_fitness','analytics_decision_state','analytics_forecast_error',
      'monitoring_thesis_transition','monitoring_model_drift','monitoring_research_postmortem',
      'governance_os_version','governance_module_version','governance_migration'
    }
    assert required <= tables, sorted(required-tables)
