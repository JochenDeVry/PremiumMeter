import pytest
import asyncio
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from src.database.connection import Base, get_db
from src.api.main import app

# Test database URL (use in-memory SQLite for fast, isolated tests)
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def db_engine():
    """
    Create a fresh database engine for each test.
    Uses in-memory SQLite for fast, isolated tests.
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Create a fresh database session for each test.
    Rollback all changes after test completes.
    """
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture(scope="function")
def test_client(db_session: Session):
    """
    Create a FastAPI test client with a test database session.
    Automatically overrides the database dependency.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

@pytest.fixture
def sample_stock_data():
    """Provide sample stock data for testing."""
    return {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
    }

@pytest.fixture
def sample_premium_data():
    """Provide sample option premium data for testing."""
    return {
        "ticker": "AAPL",
        "strike_price": 150.0,
        "expiration_date": "2024-12-20",
        "option_type": "call",
        "premium": 5.50,
    }
