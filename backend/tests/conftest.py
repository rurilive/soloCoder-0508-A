import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.connection import Base, get_db
from backend.app.models.url import URLMapping


TEST_DATABASE_URL = "sqlite:///./test_url_shortener.db"


@pytest.fixture(scope="function")
def test_engine():
    engine = create_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db_session(test_engine):
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(test_db_session):
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_url_mappings(test_db_session):
    mappings = [
        URLMapping(short_code="abc123", original_url="https://example.com"),
        URLMapping(short_code="def456", original_url="https://google.com"),
        URLMapping(short_code="ghi789", original_url="https://github.com"),
    ]
    test_db_session.add_all(mappings)
    test_db_session.commit()
    return mappings
