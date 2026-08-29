from sqlalchemy import text
from research_os.storage.db import create_session_factory

def test_session_factory_creates_working_sqlalchemy_session():
    factory=create_session_factory('sqlite+pysqlite:///:memory:')
    with factory() as session:
        assert session.execute(text('select 1')).scalar_one()==1
