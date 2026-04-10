# Synora: Audience Correlation & Reporting as a Service

A modern, distributed platform for fingerprint-based audience correlation, real-time matching, and privacy-compliant advertising intelligence.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Service URLs](#service-urls)
- [Component Descriptions](#component-descriptions)
- [Development Setup](#development-setup)
- [API Documentation](#api-documentation)
- [Database Schemas](#database-schemas)
- [Monitoring & Observability](#monitoring--observability)
- [Contributing](#contributing)
- [License](#license)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (React 18)                         │
│                      http://localhost:3000                          │
└────────────────┬────────────────────────────────────────────────────┘
                 │
      ┌──────────┴──────────┬──────────────┬────────────────┐
      │                     │              │                │
┌─────▼────────┐   ┌───────▼─────┐  ┌────▼──────────┐  ┌──▼──────────┐
│ Advertiser   │   │   Privacy   │  │    Billing   │  │  Matching  │
│     API      │   │   Service   │  │    Service   │  │   Engine   │
│   (FastAPI)  │   │ (FastAPI)   │  │  (FastAPI)   │  │  (Faust)   │
│ :8084        │   │  :8085      │  │   :8086      │  │   :8081    │
└──────────────┘   └─────────────┘  └──────────────┘  └────────────┘
      │                    │               │               │
      └────────────────────┼───────────────┴───────────────┘
                           │
                  ┌────────▼─────────┐
                  │      Kafka       │
                  │   Message Bus    │
                  │     :9092        │
                  └────┬─────────────┘
                       │
    ┌──────────────────┼──────────────────┬──────────────────┐
    │                  │                  │                  │
┌───▼─────────┐  ┌────▼──────┐  ┌───────▼────┐  ┌──────────▼──┐
│ Fingerprint │  │ Fingerprint│  │Segmentation│  │ Ingestor   │
│  Indexer    │  │  Ingestor  │  │  Engine    │  │ (Go)       │
│ (Rust)      │  │ (Go)       │  │ (Python)   │  │ :8080      │
│   :8082     │  │   :8080    │  │  :8083     │  └────────────┘
└──────┬──────┘  └────────────┘  └────────────┘
       │
   ┌───▼──────────────────┬─────────────┬────────────┐
   │                      │             │            │
┌──▼───┐  ┌──────────┐  ┌▼──────┐  ┌──▼──┐  ┌─────▼─┐
│Scylla│  │PostgreSQL│  │ Redis │  │MinIO│  │Trino │
│ DB   │  │   DB     │  │ Cache │  │S3   │  │Engine│
│:9042 │  │ :5432    │  │:6379  │  │:9000│  │:8088 │
└──────┘  └──────────┘  └───────┘  └─────┘  └──────┘

Data Pipeline (Airflow):
┌─────────────────────────────────────────────────────────┐
│         Apache Airflow                                  │
│    Scheduler + Webserver :8089                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │ • Flink Jobs  • Spark Jobs  • Data Enrichment   │ │
│  │ • Backfill    • Archive     • Reporting         │ │
│  └──────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘

Observability Stack:
┌─────────────┬──────────┬──────────┐
│ Prometheus  │  Grafana │  Jaeger  │
│  :9090      │  :3001   │ :16686   │
└─────────────┴──────────┴──────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose (v2.0+)
- Make (optional, but recommended)
- 16GB RAM, 50GB disk space

### 1. Initialize Environment

```bash
cp .env.example .env
```

### 2. Build and Start Services

```bash
docker-compose up -d
```

Wait for all services to be healthy:

```bash
docker-compose ps
```

### 3. Initialize Databases and Services

```bash
chmod +x docker-compose.init.sh
./docker-compose.init.sh
```

This script will:
- Create Kafka topics (raw.fingerprints, matched.viewership, unmatched.fingerprints, consent.events)
- Initialize ScyllaDB keyspace and tables
- Set up PostgreSQL schemas
- Create MinIO buckets

### 4. Verify Setup

Access the web UIs:

```bash
# Kafka UI - View topics and messages
open http://localhost:8080

# Grafana - Metrics and dashboards
open http://localhost:3001  # admin/admin

# Airflow - Data pipeline orchestration
open http://localhost:8089

# Frontend - Synora application
open http://localhost:3000
```

## Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Infrastructure** | | |
| Kafka | kafka:9092 | Message streaming |
| Kafka UI | http://localhost:8080 | Topic browser |
| ScyllaDB | localhost:9042 | Fingerprint database |
| PostgreSQL | localhost:5432 | Consent & billing DB |
| Redis | localhost:6379 | Cache layer |
| MinIO | http://localhost:9001 | Object storage (S3-compatible) |
| Trino | http://localhost:8088 | Query engine |
| **Core Services** | | |
| Fingerprint Ingestor | http://localhost:8080 | Ingest fingerprints |
| Matching Engine | http://localhost:8081 | Real-time matching |
| Fingerprint Indexer | http://localhost:8082 | Index fingerprints |
| Segmentation Engine | http://localhost:8083 | Audience segmentation |
| Advertiser API | http://localhost:8084 | Public API |
| Privacy Service | http://localhost:8085 | Consent management |
| Billing Service | http://localhost:8086 | Usage billing |
| **Frontend & Data** | | |
| Frontend | http://localhost:3000 | React application |
| Airflow | http://localhost:8089 | Data pipeline |
| **Observability** | | |
| Prometheus | http://localhost:9090 | Metrics collection |
| Grafana | http://localhost:3001 | Dashboards (admin/admin) |
| Jaeger | http://localhost:16686 | Distributed tracing |

## Component Descriptions

### SDK (C++17)

The native SDK for client-side fingerprint generation and data collection.

```
sdk/
├── src/               # C++17 source files
├── include/          # Header files
└── android/          # Android NDK bindings
```

Features:
- Low-latency fingerprint generation
- TLS/SSL support
- Offline capability
- Cross-platform (iOS, Android, Web)

### Services

#### Fingerprint Ingestor (Go)

High-performance HTTP service that receives fingerprint submissions from clients.

- Listens on port 8080
- Publishes to `raw.fingerprints` Kafka topic
- Rate limiting and validation
- Request deduplication via Redis

#### Fingerprint Indexer (Rust)

Consumer service that indexes fingerprints into ScyllaDB for fast lookup.

- Listens on port 8082
- Consumes `raw.fingerprints` from Kafka
- Maintains inverted indexes
- Real-time indexing with sub-second latency

#### Matching Engine (Python/Faust)

Stateful Kafka Streams application for real-time matching and correlation.

- Listens on port 8081
- Implements probabilistic matching algorithms
- Maintains rolling windows of fingerprints
- Publishes matches to `matched.viewership` topic

#### Segmentation Engine (Python)

Audience segmentation and targeting logic.

- Listens on port 8083
- Real-time segment computation
- Dynamic rule evaluation
- Redis-backed segment state

#### Advertiser API (Python/FastAPI)

RESTful API for advertisers to query matches and manage campaigns.

- Listens on port 8084
- JWT authentication
- Query fingerprint matches
- Campaign management
- Rate limiting per advertiser

#### Privacy Service (Python/FastAPI)

Manages user consent and privacy compliance.

- Listens on port 8085
- GDPR/CCPA consent tracking
- Opt-out enforcement
- Audit logging
- Consent event processing

#### Billing Service (Python/FastAPI)

Usage-based billing and invoice generation.

- Listens on port 8086
- Tracks API usage
- Stripe integration
- Monthly invoicing
- Usage reports

### Data Pipeline

#### Flink Jobs (Scala/Java)

Stream processing jobs for complex event processing.

```
data-pipeline/flink-jobs/
├── src/main/scala/
└── pom.xml
```

#### Spark Jobs (Python/Scala)

Batch processing for analytics and reporting.

```
data-pipeline/spark-jobs/
├── src/
└── build.sbt
```

#### Airflow DAGs (Python)

Orchestration of data pipeline workflows.

```
data-pipeline/airflow-dags/
├── fingerprint_backfill.py
├── daily_reporting.py
├── consent_enforcement.py
└── data_quality_checks.py
```

### Frontend (React 18 + TypeScript)

Modern dashboard for campaign management and analytics.

```
frontend/
├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   └── App.tsx
├── package.json
└── Dockerfile
```

## Development Setup

### Local Development Without Docker

For faster iteration during development:

```bash
# Backend services (each in separate terminal)
cd services/fingerprint-ingestor
go run main.go

cd services/matching-engine
python -m faust -A app worker --loglevel info

cd services/advertiser-api
uvicorn app.main:app --reload --port 8084

# Frontend
cd frontend
npm start
```

### Running Tests

```bash
# Run all tests
make test

# Run specific service tests
make test-fingerprint-ingestor
make test-advertiser-api
make test-privacy-service

# Run with coverage
make test-coverage
```

### Building SDKs

```bash
# Build C++ SDK
make sdk-build

# Build with Android support
make sdk-build-android
```

## API Documentation

### Fingerprint Ingestor

```bash
# Submit a fingerprint
curl -X POST http://localhost:8080/api/v1/fingerprints \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "uuid",
    "user_agent": "Mozilla/5.0...",
    "ip_address": "203.0.113.1",
    "metadata": {
      "timezone": "UTC",
      "language": "en"
    }
  }'

# Health check
curl http://localhost:8080/health
```

### Advertiser API

```bash
# Authenticate
curl -X POST http://localhost:8084/api/v1/auth/login \
  -d "username=advertiser@example.com&password=pass"

# Query matches
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8084/api/v1/matches?campaign_id=campaign123&limit=100

# Create campaign
curl -X POST http://localhost:8084/api/v1/campaigns \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Summer Sale 2024",
    "start_date": "2024-06-01",
    "end_date": "2024-08-31",
    "budget_cents": 1000000
  }'
```

### Privacy Service

```bash
# Get user consents
curl http://localhost:8085/api/v1/consents?user_id=user123

# Grant consent
curl -X POST http://localhost:8085/api/v1/consents \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "consent_type": "marketing",
    "granted": true
  }'

# Opt-out (GDPR right to be forgotten)
curl -X POST http://localhost:8085/api/v1/users/user123/forget-me
```

## Database Schemas

### ScyllaDB (NoSQL)

```
Keyspace: acraas

Tables:
  - fingerprints: Primary fingerprint data
  - viewer_events: Time-series viewer events
  - segments: Audience segment definitions
  - matches: Match results (windowed)
```

### PostgreSQL (Relational)

```
Databases:
  - acraas (main application DB)

Tables:
  - consents: User consent records
  - audit_logs: Compliance audit trail
  - advertisers: Advertiser profiles
  - billing_events: Usage events
  - invoices: Monthly invoices
  - api_keys: Advertiser API keys
```

## Monitoring & Observability

### Prometheus Metrics

All services expose Prometheus metrics on `/metrics` endpoint:

```bash
curl http://localhost:8084/metrics
```

Key metrics:
- `acraas_fingerprints_ingested_total` - Total fingerprints ingested
- `acraas_matches_found_total` - Total matches found
- `acraas_api_requests_duration_seconds` - API latency
- `acraas_kafka_lag` - Consumer lag

### Grafana Dashboards

Pre-built dashboards available:
- System Overview
- Service Health
- Fingerprint Pipeline
- API Performance
- Billing & Revenue

Import by accessing http://localhost:3001

### Jaeger Tracing

Full request tracing across all services:

```bash
open http://localhost:16686
```

Search for traces by:
- Service name
- Operation
- Tags (user_id, campaign_id, etc.)

## Troubleshooting

### Services not starting

```bash
# Check logs
docker-compose logs -f fingerprint-ingestor

# Check service health
docker-compose ps

# Restart a service
docker-compose restart fingerprint-ingestor
```

### Database connection issues

```bash
# Test PostgreSQL connection
docker exec acraas-postgres psql -U acraas -d acraas -c "SELECT 1"

# Test ScyllaDB connection
docker exec acraas-scylladb cqlsh -e "DESCRIBE KEYSPACES"

# Test Redis
docker exec acraas-redis redis-cli -a redispass123 ping
```

### Kafka topics not created

```bash
# Re-run initialization
./docker-compose.init.sh

# List topics
docker exec acraas-kafka kafka-topics.sh --bootstrap-server localhost:9092 --list

# Create topic manually
docker exec acraas-kafka kafka-topics.sh --bootstrap-server localhost:9092 \
  --create --topic my-topic --partitions 6 --replication-factor 1
```

## Performance Tuning

### Kafka Consumer Lag

```bash
# Check consumer lag
docker exec acraas-kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group acraas-group \
  --describe
```

### Database Connection Pooling

Adjust in `.env`:
```
POSTGRES_POOL_MIN_SIZE=10
POSTGRES_POOL_MAX_SIZE=50
REDIS_CONNECTION_POOL_SIZE=20
```

### Caching Strategy

```
# High cache TTL for static data (24h)
REDIS_CACHE_TTL=86400

# Low cache TTL for dynamic data (1h)
REDIS_DYNAMIC_TTL=3600
```

## Clean Up

```bash
# Stop all services (data preserved)
docker-compose down

# Stop and remove volumes (destructive!)
docker-compose down -v

# View logs after shutdown
docker-compose logs

# Clean rebuild
make clean && make build
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Synora is proprietary software. All rights reserved.

---

