import os

os.environ["DATABASE_URL"] = "sqlite:///./data/test_cricket_hub.db"
os.environ["CRICKET_ADMIN_EMAIL"] = "admin@example.test"
os.environ["CRICKET_ADMIN_PASSWORD"] = "test-only-password"

import pytest
from fastapi.testclient import TestClient

from backend.app.database import Base, engine
from backend.app.main import app, sessions


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
    sessions.clear()
