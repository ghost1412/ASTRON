import asyncio
import httpx
import uuid
import time
import random
import structlog

logger = structlog.get_logger(__name__)

# Config
GATEWAY_URL = "http://localhost:8000/v1/telemetry/queries/bulk"
TENANT_ID = "acme-corp"
API_TOKEN = "sk_LUFRpO8Aq09XqETG9IJg2-Bx-fB1zuo12SWFXUiFwg4"
CONCURRENCY = 20
TOTAL_REQUESTS = 1000

SQL_TEMPLATES = [
    "SELECT * FROM users WHERE id = {id}",
    "INSERT INTO logs (user_id, action) VALUES ({id}, 'login')",
    "UPDATE orders SET status = 'shipped' WHERE order_id = {id}",
    "DELETE FROM sessions WHERE expired_at < '{date}'",
    "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.total > {id}"
]

async def send_telemetry(client, request_id):
    query = random.choice(SQL_TEMPLATES).format(
        id=random.randint(1, 100000),
        date=time.strftime('%Y-%m-%d %H:%M:%S')
    )
    
    payload = {
        "db_alias": "prod_cluster_01",
        "dialect": "postgres",
        "schema_version": 1,
        "samples": [{
            "query_text": query,
            "calls_delta": 1,
            "total_exec_time_ms_delta": random.uniform(10, 500)
        }]
    }
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "X-Tenant-ID": TENANT_ID
    }
    
    start = time.perf_counter()
    try:
        resp = await client.post(GATEWAY_URL, json=payload, headers=headers)
        duration = time.perf_counter() - start
        return resp.status_code, duration
    except Exception as e:
        return 500, 0

async def main():
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=CONCURRENCY)) as client:
        print(f"🚀 Starting Ingestion Load Test: {TOTAL_REQUESTS} requests, concurrency={CONCURRENCY}...")
        
        start_time = time.perf_counter()
        tasks = [send_telemetry(client, i) for i in range(TOTAL_REQUESTS)]
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time
        
        # Stats logic
        successes = [r for r in results if r[0] == 200]
        avg_lat = sum([r[1] for r in results]) / len(results)
        throughput = len(results) / total_time
        
        print("\n" + "="*40)
        print(f"📊 Results for {TENANT_ID}")
        print(f"Total Requests: {TOTAL_REQUESTS}")
        print(f"Success Rate:   {len(successes)/TOTAL_REQUESTS*100:.1f}%")
        print(f"Avg Latency:    {avg_lat*1000:.2f}ms")
        print(f"Throughput:     {throughput:.2f} req/s")
        print("="*40)

if __name__ == "__main__":
    asyncio.run(main())
