from app.db.base import Base
from app.db.session import get_engine
from app import models  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())
