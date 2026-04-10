# Synora Platform Architecture
**Version 1.0 · April 2026**

## System Architecture Overview

The Synora (Automatic Content Recognition as a Service) platform is a distributed, cloud-native system designed to ingest, match, and monetize audio fingerprints at scale. The architecture is divided into 9 core components that operate independently but in concert.

### High-Level Architecture Diagram

```
                     ┌──────────────────────────────────────┐
                     │      TV DEVICES (Manufacturer SDKs)   │
                     │  ┌────────────────────────────────┐   │
                     │  │  Audio Capture (ALSA)          │   │
                     │  │  FFT Fingerprint Engine        │   │
                     │  │  SQLite Local Cache            │   │
                     │  │  HTTPS POST (batches)          │   │
                     │  └────────────┬───────────────────┘   │
                     └───────────────┼───────────────────────┘
                                     │ (Batch of 20 fingerprints)
                                     │ (1KB per minute)
                                     ↓
        ┌────────────────────────────────────────────────────────┐
        │         Synora Cloud Platform (AWS Multi-AZ)           │
        ├────────────────────────────────────────────────────────┤
        │                                                         │
        │  ┌─────────────────────────────────────────────────┐   │
        │  │  1. Ingestor Service (ECS Fargate)              │   │
        │  │     • Load balancing (ALB)                       │   │
        │  │     • Request validation & deduplication         │   │
        │  │     • Kafka producer → raw.fingerprints         │   │
        │  │     • Avg latency: 50ms                          │   │
        │  └─────────────────────────────────────────────────┘   │
        │                     ↓                                   │
        │  ┌─────────────────────────────────────────────────┐   │
        │  │  2. Message Queue (Kafka / Confluent)           │   │
        │  │     • Topic: raw.fingerprints (1M msg/sec)       │   │
        │  │     • Retention: 7 days                          │   │
        │  │     • Replication factor: 3                      │   │
        │  │     • 6 brokers (2 AZs per region)              │   │
        │  └─────────────────────────────────────────────────┘   │
        │                     ↓                                   │
        │  ┌─────────────────────────────────────────────────┐   │
        │  │  3. Matcher Service (Go microservice)            │   │
        │  │     • Consumes: raw.fingerprints                 │   │
        │  │     • Calls: Fingerprint Index (ScyllaDB)        │   │
        │  │     • Outputs: matched.viewership                │   │
        │  │     • 50M+ episodes/movies indexed               │   │
        │  │     • Fuzzy matching: ±2 sec drift tolerance     │   │
        │  │     • Latency: 200ms p99                         │   │
        │  │     • Throughput: 500K fingerprints/sec          │   │
        │  └─────────────────────────────────────────────────┘   │
        │                     ↓                                   │
        │  ┌─────────────────────────────────────────────────┐   │
        │  │  4. Fingerprint Index (ScyllaDB)                │   │
        │  │     • Distributed key-value store (NoSQL)        │   │
        │  │     • Sharded by fingerprint hash                │   │
        │  │     • Replicated across 3 AZs                    │   │
        │  │     • 50M episodes, each ~1KB metadata           │   │
        │  │     • ~50GB total data                           │   │
        │  │     • Queries: O(1) with hashing                │   │
        │  │     • Latency: 10-50ms p99                       │   │
        │  └─────────────────────────────────────────────────┘   │
        │                     ↓                                   │
        │  ┌─────────────────────────────────────────────────┐   │
        │  │  5. Segmentation Engine (Faust Streams)          │   │
        │  │     • Stream processing (Python)                 │   │
        │  │     • Consumes: matched.viewership               │   │
        │  │     • Applies targeting rules (DSL)              │   │
        │  │     • Computes audience cohorts                  │   │
        │  │     • Outputs: audience.segments                 │   │
        │  │     • State store: RocksDB (local)               │   │
        │  │     • Latency: 1-5 sec (micro-batching)          │   │
        │  └─────────────────────────────────────────────────┘   │
        │                     ↓                                   │
        │  ┌─────────────────────────────────────────────────┐   │
        │  │  6. Data Warehouse (Apache Iceberg + S3)         │   │
        │  │     • Columnar storage (Parquet)                 │   │
        │  │     • Immutable snapshots                         │   │
        │  │     • Schema evolution support                    │   │
        │  │     • Data lake: 1PB+ (multi-month history)       │   │
        │  │     • Query: Athena, Presto                       │   │
        │  │     • Cost: $20/TB/month (S3 storage)             │   │
        │  └─────────────────────────────────────────────────┘   │
        │                     ↓                                   │
        │  ┌─────────────────────────────────────────────────┐   │
        │  │  7. Monetization Engine (Java service)           │   │
        │  │     • OpenRTB bid requests                        │   │
        │  │     • Real-time segment matching                  │   │
        │  │     • Dynamic pricing (ML model)                  │   │
        │  │     • Latency SLA: < 5ms p99 (critical)          │   │
        │  │     • Throughput: 10K requests/sec                │   │
        │  │     • Redis cache: segment→price mappings         │   │
        │  └─────────────────────────────────────────────────┘   │
        │                     ↓                                   │
        │  ┌─────────────────────────────────────────────────┐   │
        │  │  8. Consent & Privacy Service (Node.js)          │   │
        │  │     • Manages user opt-outs                       │   │
        │  │     • GDPR/CCPA/PIPEDA compliance                 │   │
        │  │     • Data deletion workflows                     │   │
        │  │     • Audit logging (immutable)                   │   │
        │  │     • Redis: opt-out set (real-time)              │   │
        │  └─────────────────────────────────────────────────┘   │
        │                     ↓                                   │
        │  ┌─────────────────────────────────────────────────┐   │
        │  │  9. Billing & Analytics (Python Jupyter)         │   │
        │  │     • Revenue calculation                         │   │
        │  │     • Device-level attribution                    │   │
        │  │     • Monthly invoicing (Stripe)                  │   │
        │  │     • Dashboard queries                           │   │
        │  │     • Data warehouse: BigQuery / Redshift         │   │
        │  └─────────────────────────────────────────────────┘   │
        │                                                         │
        └────────────────────────────────────────────────────────┘
                             ↓
        ┌────────────────────────────────────────────────────────┐
        │         External APIs & Integrations                   │
        │  • DSP OpenRTB endpoints (Google, The Trade Desk, etc) │
        │  • Manufacturer partner portal                         │
        │  • Analytics dashboards                               │
        └────────────────────────────────────────────────────────┘
```

---

## Component Descriptions

### 1. Ingestor Service (ECS Fargate)

**Purpose**: Accept fingerprint batches from TV devices via HTTPS POST.

**Technology Stack**:
- **Language**: Go (for low latency and concurrency)
- **Framework**: Gin Web Framework
- **Deployment**: AWS ECS Fargate (containerized)
- **Load Balancing**: Application Load Balancer (ALB) with auto-scaling
- **Monitoring**: CloudWatch, Datadog

**Key Responsibilities**:
- Validate API keys and device IDs
- Deduplicate fingerprints (same device ID within 60 seconds = skip)
- Calculate device anonymization (hash with monthly salt)
- Parse batch JSON and extract fingerprints
- Produce to Kafka topic `raw.fingerprints`
- Rate limiting (per-device, per-API-key)
- Error handling and retry logic

**Throughput**: 1M fingerprints/sec sustained (scaled to 2M/sec during peak)

**Latency**: 
- P50: 15ms
- P95: 35ms
- P99: 50ms

**Scaling**:
- Horizontal: 20-100 ECS tasks (auto-scaling by CPU)
- Vertical: 1 vCPU, 2GB RAM per task
- Kafka partition count: 50 (for parallelism)

### 2. Message Queue (Kafka)

**Purpose**: Distributed message bus for decoupling components.

**Technology**: Confluent Kafka (managed service on AWS MSK)

**Configuration**:
- **Brokers**: 6 brokers across 2 AZs (high availability)
- **Replication Factor**: 3 (each message replicated to 3 brokers)
- **Topics**: 
  - `raw.fingerprints`: 50 partitions, 7-day retention
  - `matched.viewership`: 50 partitions, 90-day retention
  - `audience.segments`: 20 partitions, 2-year retention

**Throughput**: 1M messages/sec sustained (peaks to 2M/sec)

**Data Retention**:
- Raw fingerprints: 7 days (for late-arriving data)
- Matched viewership: 90 days (for billing lookups)
- Aggregated segments: 2 years (for historical analysis)

### 3. Matcher Service (Go Microservice)

**Purpose**: Match fingerprints against known content database and emit matched viewership events.

**Technology Stack**:
- **Language**: Go (high performance)
- **Database**: ScyllaDB (for fingerprint lookups)
- **Deployment**: Kubernetes (EKS)
- **Message Queue**: Kafka consumer group

**Matching Algorithm**:
```
For each fingerprint in batch:
  1. Hash fingerprint to find content candidates in ScyllaDB
  2. For each candidate (±2 sec drift):
     - Calculate confidence score (0-1)
     - Apply fuzzy matching tolerance
     - Filter out low-confidence matches
  3. If matched:
     - Emit matched_viewership event
     - Attach content_id, network, show_name, timestamp
  4. If not matched:
     - Store in unmatched fingerprints table
     - Emit after 24 hours (late-arrival handling)
```

**Matching Accuracy**:
- Exact match (confidence > 0.95): 85% of fingerprints
- Fuzzy match (confidence 0.85-0.95): 10% of fingerprints
- No match: 5% (unmatched content, user non-consent, etc)

**Latency**:
- P50: 50ms
- P95: 100ms
- P99: 200ms

**Throughput**: 500K fingerprints/sec

**Scaling**:
- Horizontal: Kubernetes consumer group (10-50 pods)
- Vertical: 2 vCPU, 4GB RAM per pod
- ScyllaDB: 9 nodes (3 nodes per AZ)

### 4. Fingerprint Index (ScyllaDB)

**Purpose**: Real-time key-value store for fingerprint-to-content mappings.

**Technology**: ScyllaDB (distributed NoSQL, Cassandra-compatible)

**Data Model**:
```
CQL Schema:
CREATE TABLE fingerprints (
    fingerprint_hash TEXT,         -- 256-bit hash in hex
    content_id INT,                -- Unique content identifier
    network TEXT,                  -- "ESPN", "HBO", "Netflix", etc
    show_name TEXT,                -- "Game of Thrones"
    episode_num INT,               -- 1
    air_date DATE,                 -- 2026-04-01
    duration_sec INT,              -- 3600
    start_time_sec INT,            -- For multi-part episodes
    confidence DECIMAL,            -- 0.95
    last_updated TIMESTAMP,
    PRIMARY KEY (fingerprint_hash)
);
```

**Data Size**:
- 50M unique episodes/movies
- 1KB metadata per entry
- Total: ~50GB

**Replication**:
- Replication factor: 3 (each data replicated to 3 nodes)
- Spread across 3 AZs for geo-redundancy
- Quorum read: 2 nodes required

**Performance**:
- Latency (read): 10-50ms p99
- Latency (write): 20-80ms p99
- Throughput: 500K ops/sec sustained
- Consistency: Eventual (with read repair)

**Maintenance**:
- Nightly compaction (4am UTC)
- Daily backup to S3 (snapshots)
- Rolling restarts every Sunday for updates

### 5. Segmentation Engine (Faust Streams)

**Purpose**: Real-time stream processing to compute audience segments based on matching results.

**Technology Stack**:
- **Language**: Python (Faust framework)
- **State Store**: RocksDB (local, durable)
- **Deployment**: Kubernetes

**Segment Rules (DSL)**:
```python
# Example: "Sports viewers in California with $50K+ income"
{
    "type": "watched_genre",
    "operator": "in",
    "values": ["sports", "football", "baseball"]
}

{
    "type": "dma",
    "operator": "in",
    "values": ["801", "803", "804"]  # CA metros
}

{
    "type": "household_income",
    "operator": "gte",
    "value": 50000
}
```

**Latency**:
- P50: 1-2 sec (micro-batching)
- P95: 3-5 sec
- P99: 8-10 sec

**Throughput**: 500K events/sec

**Scaling**:
- Horizontal: Kubernetes StatefulSet (10-50 pods)
- Vertical: 4 vCPU, 8GB RAM per pod
- Kafka partitions: 50 (one partition per pod slice)

### 6. Data Warehouse (Apache Iceberg + S3)

**Purpose**: Long-term storage and analytics on all collected viewership data.

**Technology Stack**:
- **Format**: Apache Iceberg (ACID transactions on S3)
- **Storage**: AWS S3 (cheap, durable)
- **Compute**: Athena (serverless SQL) + Presto (distributed query)
- **Schema**: Parquet (columnar, compressed)

**Data Retention Policies**:
- **Raw fingerprints**: 7 days in Kafka
- **Matched viewership**: 90 days in Iceberg
- **Aggregated segments**: 2 years in Iceberg
- **Audit logs**: 7 years (compliance requirement)

**Storage**:
- Raw data: 1PB/month (500K events/sec × 86400 sec/day × 30 days ÷ 10 compression ratio)
- Cost: ~$20/TB/month in S3 (cheaper with Glacier for >90 days)

### 7. Monetization Engine (Java Service)

**Purpose**: Real-time bidding and price discovery for audience segments.

**Technology Stack**:
- **Language**: Java/Kotlin
- **Framework**: Spring Boot
- **Cache**: Redis (segment → price mappings)
- **Protocol**: OpenRTB 2.5

**Latency SLA** (Critical):
- P50: 2-3ms
- P95: 4ms
- P99: < 5ms (non-negotiable for RTB)

**Throughput**: 10K OpenRTB requests/sec

**Pricing Model**:
```
Base Price = $0.10 (baseline CPM for generic audience)

Price Multiplier = 
    base × confidence_score × demand_multiplier × segment_rarity

Example:
- Sports fans (common segment): 1.0x multiplier = $0.10
- Premium income + sports: 2.5x multiplier = $0.25
- Rare segment (e.g., high-income + tech + Northeast): 3.5x multiplier = $0.35
```

### 8. Consent & Privacy Service (Node.js)

**Purpose**: Manage user consent, handle opt-outs, and ensure GDPR/CCPA compliance.

**Technology Stack**:
- **Language**: JavaScript (Node.js)
- **Framework**: Express.js
- **Database**: PostgreSQL (transactional)
- **Cache**: Redis (real-time opt-out set)
- **Audit**: CloudTrail + DynamoDB (immutable logs)

**Key Functions**:
- Record user consent decisions
- Process opt-out requests
- Handle data deletion (GDPR/CCPA)
- Maintain immutable audit logs
- Real-time filtering in Kafka consumers

### 9. Billing & Analytics (Python)

**Purpose**: Calculate revenue share and generate monthly invoices for manufacturers.

**Technology Stack**:
- **Language**: Python
- **Notebooks**: Jupyter
- **Database**: Data warehouse (Iceberg/Athena)
- **Invoicing**: Stripe API
- **Reporting**: Redash (visual analytics)

**Monthly Revenue Calculation**:
- Count fingerprints per device model
- Multiply by segment prices (ML-based)
- Calculate manufacturer share (30%)
- Generate Stripe invoices
- Payment via ACH or wire transfer

---

## Data Flow Narrative

### Example: A User Watches ESPN Sports

**Timeline**:

1. **T=0s: Device captures audio**
   - User's Samsung TV is playing ESPN sports content
   - SDK captures 3-second audio sample
   - FFT analysis converts to 256-bit fingerprint hash
   - Stored in SQLite cache

2. **T=60s: Batch sent to cloud**
   - SDK collects 20 fingerprints
   - HTTPS POST → `ingest.acraas.io/v1/fingerprints`

3. **T=65s: Ingestor receives batch**
   - Validates API key, dedups, anonymizes device_id
   - Produces 20 messages to Kafka topic

4. **T=75s: Matcher processes batch**
   - Looks up each fingerprint in ScyllaDB
   - Finds match: ESPN content
   - Emits matched_viewership event

5. **T=1-2s: Segmentation engine processes event**
   - Looks up device profile (income, DMA, age)
   - Evaluates segment rules
   - Updates state; emits segment_entry event

6. **T+5min: Data warehouse ingests**
   - Events batched to Parquet
   - Iceberg transaction writes to S3

7. **T+30min: Advertiser RTB bid request**
   - DSP checks: "Which devices match sports fans?"
   - Calls Synora OpenRTB API

8. **T+30min+2ms: Monetization engine responds**
   - Device matches segment; calculates price
   - Returns: match confirmed, price $0.25 CPM

9. **Month-end: Billing**
   - Query all matched_viewership for manufacturer
   - Calculate revenue; generate invoice
   - Payment processed

---

## Technology Decisions & Rationale

### Why ScyllaDB?

**Advantages**:
- **Speed**: O(1) lookups, 10-50ms latency
- **Scale**: Distributed by design; shards automatically
- **Cost**: 10x cheaper than DynamoDB per GB
- **Replication**: Native 3x replication across AZs

### Why Kafka?

**Advantages**:
- **Distributed**: Brokers replicate; survives node failures
- **Throughput**: 1M msg/sec easily; partitioned by key
- **Persistence**: Messages durable on disk; can replay
- **Multi-consumer**: Ingestor and Analytics consume same topic

### Why Faust for Stream Processing?

**Advantages**:
- **Python**: Data team comfortable; faster iteration
- **Stateful**: RocksDB embedded; fast windowed aggregations
- **Latency**: Sub-second processing; ideal for segmentation
- **Lightweight**: Single container; ~500MB RAM per pod

### Why Apache Iceberg?

**Advantages**:
- **ACID**: Transactions on S3; no vendor lock-in
- **Cost**: S3 storage is $0.023/GB/month; 10x cheaper than Snowflake
- **Schema evolution**: Add columns without rewrites
- **Time travel**: Query data from any point in time

---

## Scalability Design

### Horizontal Scaling

Each component scales independently:

**Ingestor Service**:
- Current: 20 ECS tasks
- Peak: 100 tasks (10x during major events)
- Scaling trigger: CPU > 70%

**Matcher Service**:
- Current: 30 Kubernetes pods
- Peak: 200 pods
- Scaling trigger: Kafka consumer lag > 5 min

**Kafka Brokers**:
- Current: 6 brokers
- Adding brokers: No downtime; cluster rebalances automatically

**ScyllaDB Nodes**:
- Current: 9 nodes (3 per AZ)
- Adding nodes: Streaming rebalance (no locks)

### Vertical Scaling

**Ingestor**:
- Increase vCPU from 1 to 2
- Increase network bandwidth (4 Gbps in ECS)

**Matcher**:
- Increase vCPU from 2 to 4
- Increase ScyllaDB connection pool

**Kafka**:
- Upgrade disk from HDD to NVMe SSD
- Increase network throughput

### Partition Strategy

**Kafka Topics** (partitioned by device_id hash):
- `raw.fingerprints`: 50 partitions
- `matched.viewership`: 50 partitions
- Ensures ordering within device, parallelism across devices

**ScyllaDB** (partitioned by fingerprint hash):
- Ring-based: fingerprint % num_vnodes
- 256 vnodes per node (9 nodes = 2304 vnodes)
- Uniform data distribution

**Data Warehouse** (partitioned by time):
- Year/month/day/hour
- Pruning: Queries only scan relevant partitions

---

## Privacy-by-Design Principles

### Applied Throughout

**1. Anonymization at Ingest**:
- Device ID: Hashed (salt per month)
- IP address: Truncated to /24 prefix
- Timestamp: Rounded to minute granularity

**2. Consent Enforcement**:
- Ingestor checks Redis opt-out set
- Matcher skips opted-out devices
- Monetization excludes opted-out from bidding

**3. Immutable Audit Logs**:
- Every consent change logged to DynamoDB
- Write-once, no deletes
- Retention: 7 years

**4. Data Minimization**:
- Never collect: Raw audio, full IP, MAC address
- Collect only: Fingerprint hash, network, show name, timestamp

**5. Right to Access (GDPR)**:
- User requests data export
- Privacy service queries Iceberg
- Returns: All matched programs, timestamps

**6. Right to Deletion (GDPR)**:
- User requests erasure
- Batch job queries Iceberg
- Deletes rows using Iceberg transactions (ACID)

---

## Disaster Recovery Strategy

### RTO & RPO Goals

**RTO** (Recovery Time Objective): < 1 hour  
**RPO** (Recovery Point Objective): < 5 minutes

### Failure Scenarios

**ScyllaDB Node Failure**:
- RTO: 0 (automatic failover)
- RPO: 0 (replicated to 2 other nodes)

**Kafka Broker Failure**:
- RTO: 10 minutes
- RPO: 0 (replicated to 2 other brokers)

**Ingestor Service Outage**:
- RTO: 5 minutes (auto-restart)
- RPO: 2 minutes (last batch)

**Complete Region Failure**:
- RTO: 5-10 minutes (DNS failover)
- RPO: 5 minutes (replica catch-up)

**Data Warehouse Corruption**:
- RTO: < 1 hour (rollback snapshot)
- RPO: 1 day (last good snapshot)

### Backup & Replication

| Component | Backup Method | Frequency | Retention | RTO |
|---|---|---|---|---|
| ScyllaDB | Snapshots to S3 | Daily | 30 days | 2 hours |
| PostgreSQL | Binary replication | Continuous | 7 days | 5 min |
| Kafka | Replication factor 3 | N/A | 7 days | 0 |
| S3 | Cross-region replication | Continuous | 2 years | 0 |
| Redis | Not critical | N/A | N/A | 5 min |

---

## Monitoring & Alerts

**Key Metrics**:
- Kafka consumer lag (alert if > 5 min)
- ScyllaDB query latency (p99 > 100ms)
- Ingestor error rate (> 1%)
- Matcher unmatched rate (> 10%)
- Data warehouse query errors (> 0.1%)

**On-Call Escalation**:
1. Automated alert + Slack notification
2. On-call engineer (5 min response time)
3. Engineering manager (escalation after 30 min)
4. VP Engineering (critical outage affecting customers)

---

## Conclusion

The Synora platform achieves:
- **Scale**: 1M fingerprints/sec, 2.9B devices tracked
- **Latency**: < 5ms RTB, < 200ms matching
- **Reliability**: 99.9% uptime, < 1 hour RTO
- **Privacy**: Anonymization, consent enforcement, GDPR/CCPA compliance
- **Cost**: $20/TB/month storage, $0.001 per fingerprint processed

The architecture prioritizes independent scaling, data immutability, and privacy-by-design to serve the TV advertising ecosystem efficiently and ethically.

---

**Document Version**: 1.0  
**Last Updated**: April 2026  
**Authors**: Synora Platform Team  
**Contact**: architecture@acraas.io
