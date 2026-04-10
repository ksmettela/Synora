import os
import logging
from fastapi import FastAPI
from sqlalchemy import create_engine
from prometheus_client import Counter, Histogram, start_http_server
from datetime import datetime

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

app = FastAPI(title="Billing Service")
billing_events = Counter('acraas_billing_events_total', 'Total billing events', ['type'])
invoice_amount = Histogram('acraas_invoice_amount_cents', 'Invoice amounts in cents')

@app.on_event("startup")
async def startup():
    try:
        db_url = os.getenv('POSTGRES_URL', 'postgresql://acraas:acraas_pass@localhost:5432/acraas')
        engine = create_engine(db_url)
        logger.info("Connected to PostgreSQL")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
    
    start_http_server(8086)
    logger.info("Prometheus metrics started")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "billing-service"}

@app.get("/api/v1/advertisers/{advertiser_id}/invoices")
async def get_invoices(advertiser_id: str):
    return {"advertiser_id": advertiser_id, "invoices": []}

@app.get("/api/v1/advertisers/{advertiser_id}/usage")
async def get_usage(advertiser_id: str):
    return {"advertiser_id": advertiser_id, "total_cost_cents": 0, "period": "current_month"}

@app.post("/api/v1/billing/events")
async def record_billing_event(advertiser_id: str, event_type: str, amount_cents: int):
    billing_events.labels(type=event_type).inc()
    invoice_amount.observe(amount_cents)
    return {"status": "recorded", "event_type": event_type, "amount_cents": amount_cents}
