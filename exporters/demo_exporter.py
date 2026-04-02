import requests
import json
import time

API_BASE = "http://localhost:8000"

def simulate_onboarding():
    print("--- Onboarding ---")
    company_id = f"test-company-{int(time.time())}"
    res = requests.post(f"{API_BASE}/v1/onboarding/register?company_id={company_id}&company_name=Test+Company")
    data = res.json()
    print(f"Registered: {data}")
    return data["api_token"]

def push_sample_telemetry(token):
    print("--- Pushing Telemetry ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Push Assets
    assets_payload = {
        "db_alias": "prod-db",
        "data_assets": [
            {
                "asset_name": "users",
                "asset_type": "TABLE",
                "schema_ddl": "CREATE TABLE users (id UUID, name TEXT, email TEXT)",
                "schema_version": 1
            }
        ]
    }
    requests.post(f"{API_BASE}/v1/telemetry/assets", json=assets_payload, headers=headers)
    
    # 2. Push Queries
    queries_payload = {
        "db_alias": "prod-db",
        "dialect": "postgres",
        "samples": [
            {
                "query_text": "SELECT * FROM users WHERE email = 'test@example.com'",
                "calls_delta": 10,
                "total_exec_time_ms_delta": 50,
                "timestamp": "2023-11-27T10:00:00Z"
            }
        ]
    }
    requests.post(f"{API_BASE}/v1/telemetry/queries/bulk", json=queries_payload, headers=headers)
    print("Telemetry pushed.")

if __name__ == "__main__":
    # Note: Gateway must be running (uvicorn gateway.main:app)
    # This script is for demonstration/testing.
    try:
        token = simulate_onboarding()
        push_sample_telemetry(token)
        print("Success! Check the dashboard.")
    except Exception as e:
        print(f"Error: {e}. Is the server running?")
