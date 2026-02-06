import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def setup_test_db_url():
    test_db = Path("./test.db")
    if test_db.exists():
        test_db.unlink()
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
    os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/1"
    os.environ["ENV"] = "test"
    os.environ["API_AUTH_ENABLED"] = "false"
    os.environ["CELERY_EAGER_MODE"] = "true"

    from app.core.config import get_settings
    from app.db.session import reset_session_for_tests

    get_settings.cache_clear()
    reset_session_for_tests()

    yield

    if test_db.exists():
        test_db.unlink()


@pytest.fixture
def client(setup_test_db_url):
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
