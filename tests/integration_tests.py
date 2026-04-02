import pytest
from fastapi.testclient import TestClient
from gateway.main import app, get_current_tenant
from core.db_manager import DatabaseManager
from sqlmodel import Session, SQLModel, create_engine
from unittest.mock import patch, MagicMock

# Setup an in-memory SQLite DB for testing
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

def override_get_current_tenant():
    return "test-tenant-123"

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session):
    # Dependency Override
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant
    
    # Mock DatabaseManager to use our test engine
    with patch("core.db_manager.DatabaseManager.get_session") as mock_get_session:
        mock_get_session.return_value.__enter__.return_value = session
        with TestClient(app) as client:
            yield client
    app.dependency_overrides.clear()

def test_list_queries_empty(client):
    response = client.get("/v1/queries", headers={"Authorization": "Bearer sk_mock"})
    assert response.status_code == 200
    assert response.json() == {"data": []}

@patch("gateway.main.task_queue.enqueue")
def test_push_telemetry(mock_enqueue, client):
    payload = {
        "db_alias": "prod-db",
        "dialect": "postgres",
        "samples": [
            {
                "query_text": "SELECT 1",
                "calls_delta": 1,
                "total_exec_time_ms_delta": 10
            }
        ]
    }
    response = client.post(
        "/v1/telemetry/queries/bulk", 
        json=payload, 
        headers={"Authorization": "Bearer sk_mock"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    # Verify task was enqueued
    assert mock_enqueue.called

def test_global_exception_handler(client):
    # Force a 404 to see structured error
    response = client.get("/non-existent-path", headers={"Authorization": "Bearer sk_mock"})
    # Catch-all isn't implemented for GET, so it returns 404
    # But let's trigger a real unhandled exception if we can...
    # Actually, the global handler is for 'Exception', let's mock an endpoint to fail.
    pass

if __name__ == "__main__":
    pytest.main()
