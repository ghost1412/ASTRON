import pytest
from fastapi.testclient import TestClient
from gateway.main import app

client = TestClient(app)

def test_health_check():
    """Verify the platform is up."""
    response = client.get("/health")
    assert response.status_code == 200

def test_onboarding():
    """Verify company registration."""
    # Using a random ID to avoid collision if run multiple times locally
    import secrets
    company_id = f"test-{secrets.token_hex(4)}"
    response = client.post(f"/v1/onboarding/register?company_id={company_id}&company_name=TestCorp")
    assert response.status_code == 200
    assert "token" in response.json()

def test_telemetry_bulk_ingest_no_auth():
    """Verify auth middleware blocks unauthenticated requests."""
    payload = {"samples": [{"query_text": "SELECT 1", "user_id": "u1"}]}
    response = client.post("/v1/telemetry/queries/bulk", json=payload)
    assert response.status_code == 403

def test_query_filtering():
    """Verify that retrieval filters (dialect, user_id) are accepted."""
    headers = {"Authorization": "Bearer sk_demo_token_123"}
    # The endpoint should accept these params even if no data matches yet
    response = client.get("/v1/queries?dialect=postgres&user_id=u1", headers=headers)
    assert response.status_code == 200
    assert "data" in response.json()

