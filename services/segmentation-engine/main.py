import os
import logging
from fastapi import FastAPI
from prometheus_client import Counter, start_http_server
import aioredis

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

app = FastAPI(title="Segmentation Engine")
segments_computed = Counter('acraas_segments_computed_total', 'Total segments computed')

redis_pool = None

@app.on_event("startup")
async def startup():
    global redis_pool
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    try:
        redis_pool = await aioredis.create_redis_pool(redis_url, db=2)
        logger.info("Connected to Redis")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
    
    start_http_server(8083)
    logger.info("Prometheus metrics started")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "segmentation-engine"}

@app.get("/metrics")
async def metrics():
    return "# HELP acraas_segments_computed_total Total segments computed\n# TYPE acraas_segments_computed_total counter\nacraas_segments_computed_total 0\n"

@app.post("/api/v1/segments/compute")
async def compute_segment(segment_id: str):
    segments_computed.inc()
    return {"segment_id": segment_id, "status": "computed"}
