# Synora Data Pipeline

Three integrated components for real-time viewership ingestion, batch
aggregation, and orchestrated processing.

## Components

### Flink Iceberg Ingestion (streaming)
Consumes matched viewership from Kafka, enriches with household ID, writes
to Iceberg.
Path: `flink-jobs/`

### Spark Aggregation & Maintenance (batch)
Daily household rollups with 7-day windows, retention enforcement (90/365
day policies), Iceberg table maintenance.
Path: `spark-jobs/`

### Airflow Orchestration (scheduling)
4 DAGs: `nightly_segmentation`, `data_retention`, `manufacturer_payouts`,
`sdk_health_check`. Custom Trino and Redis operators.
Path: `airflow-dags/`

### Seeder (reference catalog ingestion)
Populates ScyllaDB with reference fingerprints from a content catalog.
Shells out to `fingerprint_cli` so device and cloud share the same
algorithm.
Path: `seed/`

## Quick Start

```bash
# Flink
cd flink-jobs && mvn clean package -DskipTests

# Spark
cd ../spark-jobs && sbt assembly

# Airflow
cd ../airflow-dags && docker build -t acraas-airflow:latest . && \
  docker run -d -p 8080:8080 acraas-airflow:latest

# Seeder (requires fingerprint_cli built — see sdk/README.md)
python3 seed/scripts/generate_demo_wavs.py
python3 seed/seed_reference_catalog.py \
  --catalog seed/catalogs/demo.json \
  --fingerprint-cli /path/to/fingerprint_cli \
  --indexer-url http://localhost:8082
```

## Flow

```
Device SDK ─► Kafka (raw.fingerprints)
                  │
                  ├─► Matching Engine ─► Kafka (matched.viewership)
                  │                           │
                  │                           ▼
                  │                       Flink ─► Iceberg (data lake)
                  │                                    │
                  │                                    ▼
                  │                              Spark (daily rollups)
                  │                                    │
                  │                                    ▼
                  └─────────── Airflow ──────────► Redis / PostgreSQL
```

See `docs/ARCHITECTURE.md` (repo root) for the full platform architecture.
