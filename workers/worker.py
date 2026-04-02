import os
import redis
from rq import Worker, Queue

# Connect to Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
redis_conn = redis.Redis(host=REDIS_HOST, port=6379)

if __name__ == "__main__":
    listen = ["default"]
    
    worker = Worker(listen, connection=redis_conn)
    print(f"[*] Worker started. Listening on {listen}...")
    worker.work()
