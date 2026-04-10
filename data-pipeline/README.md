# ACRaaS Data Pipeline

Production-ready data pipeline for the Ad Credit as a Service platform. This repository contains three integrated components for real-time viewership ingestion, daily aggregation, and orchestrated processing.

## Quick Start

```bash
# 1. Build Flink Job
cd flink-jobs
mvn clean package -DskipTests

# 2. Build Spark Jobs
cd ../spark-jobs
sbt assembly

# 3. Deploy Airflow
cd ../airflow-dags
docker build -t acraas-airflow:latest .
docker run -d -p 8080:8080 acraas-airflow:latest
```

## Components

### 1. Flink Iceberg Ingestion (Real-time)
- Consumes matched viewership events from Kafka
- Enriches with household ID derivation
- Writes to Iceberg data lake
- Path: `flink-jobs/`

### 2. Spark Aggregation & Maintenance (Batch)
- Daily household aggregation with 7-day windows
- Data retention enforcement (90/365 day policies)
- Iceberg table maintenance and optimization
- Path: `spark-jobs/`

### 3. Airflow Orchestration (Scheduling)
- 4 DAGs: nightly_segmentation, data_retention, manufacturer_payouts, sdk_health_check
- Custom Trino and Redis operators
- Automated monitoring and alerting
- Path: `airflow-dags/`

## Architecture

```
Kafka → Flink → Iceberg → Spark Aggregation → Iceberg → Airflow → Redis/PostgreSQL
                                                              ↓
                                                         Monitoring
```

## Configuration

See `COMPONENT_SUMMARY.md` for detailed configuration variables and deployment instructions.

## Files Overview

- **FILES_CREATED.txt** - Complete list of created files
- **COMPONENT_SUMMARY.md** - Detailed architecture and implementation guide
- **README.md** - This file

## Key Features

- Real-time processing with exactly-once semantics
- ACID transactions via Iceberg
- Automated data retention enforcement
- Household segmentation and Redis population
- Manufacturer revenue share calculations
- Comprehensive monitoring and alerting

## Documentation

Detailed documentation is available in:
- `COMPONENT_SUMMARY.md` - Full implementation details
- `FILES_CREATED.txt` - File inventory and descriptions

## Status

All components are production-ready with no placeholders or mock code.
