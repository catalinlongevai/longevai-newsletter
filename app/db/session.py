from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine = None
_session_maker = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def get_session_maker():
    global _session_maker
    if _session_maker is None:
        _session_maker = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine(), class_=Session
        )
    return _session_maker


def reset_session_for_tests() -> None:
    global _engine, _session_maker
    _engine = None
    _session_maker = None


def get_db() -> Generator[Session, None, None]:
    db = get_session_maker()()
    try:
        yield db
    finally:
        db.close()
