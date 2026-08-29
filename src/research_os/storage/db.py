from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_session_factory(url: str, **engine_kwargs):
    """Return a SQLAlchemy 2.x session factory for the configured Research OS store."""
    engine = create_engine(url, **engine_kwargs)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
