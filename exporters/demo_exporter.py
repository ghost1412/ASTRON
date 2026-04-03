import requests
import json
import time
import argparse

API_BASE = "http://localhost:8000"

def simulate_onboarding(company_id):
    print("--- Onboarding ---")
    res = requests.post(f"{API_BASE}/v1/onboarding/register?company_id={company_id}&company_name=Test+Company")
    data = res.json()
    
    if res.status_code == 400:
        print(f"Company {company_id} already exists. Using fallback.")
        return company_id, "sk_demo_token_123"
    
    print(f"Registered New: {data}")
    return company_id, data.get("api_token", "sk_demo_token_123")

def sync_catalog(tenant_id, token):
    """Infrequent: Sync database structural metadata (DDL)."""
    print(f"--- Syncing Catalog for {tenant_id} ---")
    payload = {
        "db_alias": "prod-db",
        "data_assets": [
            {
                "asset_name": "users",
                "asset_type": "TABLE",
                "schema_ddl": "CREATE TABLE users (id SERIAL PRIMARY KEY, name TEXT, email TEXT)",
                "schema_version": 1
            }
        ]
    }
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}
    res = requests.post(f"{API_BASE}/v1/assets", json=payload, headers=headers)
    print(f"Catalog Sync: {res.status_code} {res.text}")

def push_sample_telemetry(tenant_id, token):
    """Frequent: Push high-volume query stream."""
    print(f"--- Pushing Telemetry for {tenant_id} ---")
    payload = {
        "db_alias": "prod-db",
        "dialect": "postgres",
        "schema_version": 1,
        "samples": [
            {
                "query_text": "SELECT * FROM users WHERE email = 'test@example.com'",
                "calls_delta": 10,
                "total_exec_time_ms_delta": 500.0
            }
        ]
    }
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}
    res = requests.post(f"{API_BASE}/v1/telemetry/queries/bulk", json=payload, headers=headers)
    print(f"Telemetry pushed: {res.status_code} {res.text}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASTRON Demo Telemetry Exporter")
    parser.add_argument("--tenant", type=str, default="abc", help="Tenant ID")
    args = parser.parse_args()

    try:
        tenant_id, token = simulate_onboarding(args.tenant)
        sync_catalog(tenant_id, token)
        push_sample_telemetry(tenant_id, token)
        print("Success! Check the dashboard. Token:", token)
    except Exception as e:
        print(f"Error: {e}. Is the server running?")
