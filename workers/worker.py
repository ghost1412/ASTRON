import os
import redis
import random
import time
from rq import Worker, Queue

# Connect to Redis - targeting 'redis' host for Docker mesh
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
redis_conn = redis.Redis(host=REDIS_HOST, port=6379, socket_timeout=5)

def discover_queues():
    """
    v4.0 Deterministic Autonomous Discovery: Identifies shards from env configuration.
    Ensures zero-touch scaling and immediate fair-share on first boot.
    """
    # 1. Deterministic Shard Generation from Orchestration
    shard_count = int(os.getenv("SHARD_COUNT", "3"))
    shard_queues = [f"shard_{i+1}" for i in range(shard_count)]
    
    # 2. Randomized Priority Shuffle
    # Every worker gets a unique queue-listening order to prevent 'Noisy Neighbor' lock-in.
    random.shuffle(shard_queues)
    
    # 3. Append default as low-priority fallback
    return shard_queues + ["default"]

if __name__ == "__main__":
    # Small delay to ensure Redis is ready in the mesh
    time.sleep(2)
    
    queues = discover_queues()
    print(f"[*] Autonomous Worker started. Self-organizing across: {queues}")
    
    worker = Worker(queues, connection=redis_conn)
    worker.work()
