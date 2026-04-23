# Synora: An Open ACR Data Platform

**A privacy-preserving Automatic Content Recognition platform for smart TV ecosystems — from on-device fingerprinting to audience monetization.**

---

## What ACR Solves

Most TV advertising still flies blind. When a spot runs on a broadcast or streaming channel, the advertiser rarely knows *which specific households saw it*, what else those households were watching that evening, or how to reach the same audience again with a follow-up creative. Automatic Content Recognition (ACR) closes that gap: by identifying what a TV is playing, second by second, platforms can build addressable audience segments and attach real delivery data to every impression.

A small number of TV manufacturers operate their own vertically integrated ACR stacks, and they monetize the resulting data at premium CPMs. For everyone else — the long tail of smart-TV OEMs, streaming-stick vendors, and set-top-box makers — the economic path to that same data is effectively closed, because building the pipeline end-to-end requires an SDK, a reference content database, a matching engine, a segmentation layer, an RTB front door, and a privacy/compliance program. That is a lot of distinct engineering and legal work to justify for any one OEM.

Synora is a reference architecture for this end-to-end system: a turnkey ACR SDK that a manufacturer can embed in firmware, a cloud platform that handles fingerprint matching, audience segmentation, and bidding integration, and a revenue-share model that aligns incentives between the platform operator and OEM partners.

The defensibility of an ACR platform is not the algorithm — the algorithms are well understood — but the combination of device footprint, content reference data, and compliance posture. Those compound slowly.

---

## What Synora Does

At its core, Synora answers one question at scale: *"What is this TV playing right now?"*

On each integrated device, the SDK periodically captures a short audio snippet from the TV's audio bus, converts it into a one-way fingerprint hash, and batches these fingerprints for transmission. In the cloud, the platform matches each incoming fingerprint against a reference database of broadcast and streaming content. When a match lands, the platform knows a specific (anonymized) device watched a specific program at a specific moment. Aggregated across millions of devices, this produces a granular view of TV viewership suitable for audience segmentation and addressable advertising.

The important design constraint is what the platform does *not* collect:

- Raw audio never leaves the device.
- Full IP addresses are truncated before storage.
- Hardware identifiers (MAC, serial) are never transmitted.
- Device IDs are derived through a salted hash that rotates on a monthly schedule, so the same physical device cannot be re-linked across months without a compromise of the salting infrastructure.

Privacy is a first-class design constraint, not a feature bolted on at the end.

---

## Platform Architecture

Synora is a distributed, cloud-native system designed around stream processing. The data path is append-only, every component is independently scalable, and the boundaries between services are either HTTP (for request/response) or Kafka (for fan-out).

### System Architecture Overview

```mermaid
graph TB
    subgraph "TV Devices (Manufacturer Firmware)"
        SDK["ACR SDK<br/>(C++17, small footprint)"]
        AC["Audio Capture<br/>(ALSA / HDMI ARC)"]
        FFT["FFT Fingerprint<br/>Engine"]
        LC["SQLite Local<br/>Cache (encrypted)"]
        AC --> FFT --> LC
        LC --> SDK
    end

    SDK -->|"HTTPS POST<br/>batched fingerprints"| LB

    subgraph "Cloud Platform (Multi-AZ)"
        LB["Load Balancer"]

        subgraph "Ingestion Layer"
            ING["Fingerprint Ingestor<br/>(Go) :8080"]
        end

        subgraph "Message Bus"
            KAFKA["Apache Kafka"]
        end

        subgraph "Processing Layer"
            MATCH["Matching Engine<br/>(Python / Faust) :8081"]
            IDX["Fingerprint Indexer<br/>(Rust) :8082"]
            SEG["Segmentation Engine<br/>(Python) :8083"]
        end

        subgraph "Data Stores"
            SCYLLA["ScyllaDB<br/>(reference index)"]
            PG["PostgreSQL<br/>(consent, billing)"]
            REDIS["Redis<br/>(cache, opt-out set)"]
            S3["Object Store + Iceberg<br/>(data warehouse)"]
        end

        subgraph "Business Layer"
            ADV["Advertiser API<br/>(FastAPI) :8084"]
            PRIV["Privacy Service<br/>(FastAPI) :8085"]
            BILL["Billing Service<br/>(FastAPI) :8086"]
        end

        subgraph "Data Pipeline"
            AIRFLOW["Apache Airflow"]
            FLINK["Flink Jobs"]
            SPARK["Spark Jobs"]
        end

        LB --> ING
        ING --> KAFKA
        KAFKA --> MATCH
        KAFKA --> IDX
        KAFKA --> SEG
        IDX --> SCYLLA
        MATCH --> SCYLLA
        MATCH --> KAFKA
        SEG --> REDIS
        SEG --> KAFKA
        ADV --> PG
        ADV --> REDIS
        PRIV --> PG
        PRIV --> REDIS
        BILL --> PG
        AIRFLOW --> FLINK
        AIRFLOW --> SPARK
        FLINK --> S3
        SPARK --> S3
    end

    subgraph "External Integrations"
        DSP["DSPs<br/>(via OpenRTB)"]
        PORTAL["Partner Portal"]
        DASH["Analytics<br/>Dashboards"]
    end

    ADV --> DSP
    ADV --> PORTAL
    BILL --> DASH

    subgraph "Observability"
        PROM["Prometheus"]
        GRAF["Grafana"]
        JAEG["Jaeger Tracing"]
    end
```

### Technology Stack at a Glance

| Layer | Technology | Why This Choice |
|---|---|---|
| **Device SDK** | C++17, ALSA, SQLite | Runs on constrained TV hardware, small binary, cross-platform |
| **Ingestion** | Go | High-throughput HTTP, low memory overhead, good fit for I/O-heavy services |
| **Message Bus** | Apache Kafka | High-throughput durable log, multi-consumer fan-out, replayable |
| **Matching** | Python (Faust streams) | Stateful stream processing with RocksDB, rapid iteration |
| **Indexing** | Rust | Memory safety, predictable latency, efficient ScyllaDB driver |
| **Fingerprint DB** | ScyllaDB | Wide-column store with predictable low-latency lookups |
| **APIs** | Python (FastAPI) | Async request handling, auto-generated OpenAPI docs |
| **Data Warehouse** | Apache Iceberg on object storage | ACID on cheap storage, schema evolution, time-travel queries |
| **Stream Processing** | Apache Flink | Exactly-once semantics, event-time windowing |
| **Batch Processing** | Apache Spark | Large-scale aggregation and retention jobs |
| **Orchestration** | Apache Airflow | DAG-based scheduling, backfill, alerting |
| **Frontend** | React 18 + TypeScript | Dashboard for campaign and segment management |
| **Infrastructure** | Terraform + Helm + Kubernetes | Reproducible, versioned cloud infrastructure |

---

## The Fingerprint Pipeline: From Sound Wave to Match

The heart of the platform is the journey of a single audio fingerprint from capture on a TV to a matched viewership event the rest of the system can reason about.

### End-to-End Data Flow

```mermaid
sequenceDiagram
    participant TV as TV Device (SDK)
    participant ING as Ingestor (Go)
    participant KFK as Kafka
    participant MAT as Matcher (Faust)
    participant SCY as ScyllaDB
    participant SEG as Segmentation Engine
    participant ICE as Iceberg (Data Lake)
    participant ADV as Advertiser API
    participant DSP as DSP
    participant BIL as Billing Service

    Note over TV: User watches a broadcast

    TV->>TV: Capture short audio window
    TV->>TV: FFT → 256-bit fingerprint
    TV->>TV: Store in SQLite cache

    Note over TV: Periodically...

    TV->>ING: HTTPS POST batched fingerprints
    ING->>ING: Validate API key, dedup, anonymize device_id
    ING->>KFK: Produce → raw.fingerprints topic

    KFK->>MAT: Consume fingerprint batch
    MAT->>SCY: Lookup fingerprint hash (hamming-tolerant)
    SCY-->>MAT: Match + confidence
    MAT->>KFK: Produce → matched.viewership topic

    KFK->>SEG: Consume matched event
    SEG->>SEG: Evaluate segment rules (genre + DMA + income)
    SEG->>SEG: Update device segment membership
    SEG->>KFK: Produce → audience.segments topic

    Note over ICE: Periodically...
    KFK->>ICE: Batch write (Parquet → Iceberg)

    Note over DSP: On bid request...
    DSP->>ADV: OpenRTB bid request
    ADV->>ADV: Lookup segments, compute price
    ADV-->>DSP: Response with match + CPM

    Note over BIL: Month end...
    BIL->>ICE: Query all matched viewership
    BIL->>BIL: Compute revenue + partner share
    BIL->>BIL: Generate invoices
```

### What Happens at Each Stage

**Stage 1 — Audio capture & fingerprinting (on-device).** The SDK captures a short audio sample from the HDMI audio bus or the platform's native audio capture API, downmixes to mono, runs an FFT, and reduces the result to a compact fingerprint hash. The hash is deterministic (the same audio always produces the same hash) but irreversible (the original audio cannot be reconstructed from it).

**Stage 2 — Batch transmission.** Fingerprints accumulate in an encrypted SQLite cache on the device that survives reboots and offline periods. The SDK batches fingerprints into a single HTTPS POST on a fixed cadence. When the network is unavailable, the cache holds a bounded number of fingerprints and retries with exponential backoff.

**Stage 3 — Ingestion & validation (Go service).** The Go-based ingestor receives batches, validates the API key, deduplicates repeats within a short window, anonymizes the device ID with a monthly rotating salt, and produces individual messages onto the `raw.fingerprints` Kafka topic. It is designed to scale horizontally behind a load balancer.

**Stage 4 — Content matching (Python/Faust).** The matching engine consumes from `raw.fingerprints`, performs a hamming-tolerant lookup against the reference index in ScyllaDB, scores the match, and emits `matched.viewership` events. Fingerprints that do not match any reference go to an unmatched queue for late-arrival handling.

**Stage 5 — Audience segmentation (Python).** Matched viewership events flow into the segmentation engine, where a rule engine combines genre, geography (DMA), household income bracket, and behavioral signals to place devices into advertiser-defined cohorts. Segment membership is pushed to Redis for fast lookup during bid requests.

**Stage 6 — Data warehouse (Iceberg on object storage).** All events — raw fingerprints, matched viewership, segment transitions — land in Iceberg tables in Parquet columnar format. This provides ACID transactions, schema evolution, and time-travel queries over a large-scale data lake on commodity object storage.

**Stage 7 — Monetization (OpenRTB).** When a demand-side platform sends a bid request targeting a segment, the advertiser API consults Redis segment state and responds with a match decision and price. CPMs scale with segment narrowness: common segments are priced cheaply, rare intersections command premiums.

**Stage 8 — Revenue & billing.** At month end, the billing service queries the warehouse for all matched viewership attributed to each partner, computes revenue, applies the partner share, and generates invoices.

---

## The SDK

The SDK is the foundational piece — an embedded C++17 library designed to run on resource-constrained smart-TV hardware.

### SDK Architecture

```mermaid
graph LR
    subgraph "ACR SDK (C++17)"
        direction TB

        API["Public C ABI<br/><code>acr.h</code>"]

        subgraph "Core Modules"
            AC["Audio Capture<br/><code>audio_capture.cpp</code><br/>ALSA integration<br/>16 kHz mono PCM"]
            FP["Fingerprint Engine<br/><code>fingerprint.cpp</code><br/>Cooley-Tukey FFT<br/>256-bit hash"]
            DI["Device Identity<br/><code>device_id.cpp</code><br/>SHA-256 + monthly salt"]
            CA["Local Cache<br/><code>cache.cpp</code><br/>SQLite WAL mode"]
            NW["Network Client<br/><code>network.cpp</code><br/>libcurl HTTPS<br/>Exponential backoff"]
            CO["Consent Manager<br/><code>consent.cpp</code><br/>Opt-in state<br/>Purge on opt-out"]
        end

        API --> AC
        API --> FP
        API --> DI
        API --> CA
        API --> NW
        API --> CO
        AC --> FP
        FP --> CA
        CA --> NW
        CO --> CA
    end

    subgraph "Platform Bindings"
        AND["Android (Kotlin)<br/>JNI Wrapper"]
        IOS["iOS (Swift)<br/>C Bridge"]
        LIN["Linux / Tizen / webOS<br/>Native"]
    end

    API --> AND
    API --> IOS
    API --> LIN
```

### SDK Design Targets

| Property | Target |
|---|---|
| Binary size | Small (single-digit MB) |
| Memory footprint | Low tens of MB RAM |
| CPU usage | Low single-digit percent on a background thread |
| Audio sample | Short window (~3 s) captured on a periodic cadence |
| Transmission | Batched fingerprints over HTTPS |
| Bandwidth | ~1 KB per minute sustained |
| Local cache | Bounded, survives reboot |
| Encryption | TLS for transport, encrypted local cache |
| Platforms | Android TV, Tizen, webOS, Linux-based TV OSes |

### SDK State Machine

```mermaid
stateDiagram-v2
    [*] --> UNINITIALIZED
    UNINITIALIZED --> INITIALIZED: acr_init(config)
    INITIALIZED --> RUNNING: acr_start()
    RUNNING --> STOPPED: acr_stop()
    STOPPED --> RUNNING: acr_start()
    STOPPED --> UNINITIALIZED: acr_shutdown()
    RUNNING --> UNINITIALIZED: acr_shutdown()
    UNINITIALIZED --> [*]

    state RUNNING {
        [*] --> Capturing
        Capturing --> Fingerprinting: audio sample
        Fingerprinting --> Caching: 256-bit hash
        Caching --> Transmitting: batched
        Transmitting --> Capturing: wait
    }
```

### Integration (C)

```c
#include "acr.h"

acr_config config = {
    .api_key = "partner_key_...",
    .endpoint = "https://ingest.synora.example",
};
acr_init(&config);

// Start capturing after the user has opted in.
acr_set_consent(true);
acr_start();

// On opt-out, purge local cache and stop capture.
acr_set_consent(false);
```

---

## Microservices Overview

### Service Communication Map

```mermaid
graph TD
    subgraph "Synchronous (HTTP / gRPC)"
        FE["Frontend<br/>(React)"] -->|REST| ADV["Advertiser API"]
        FE -->|REST| PRIV["Privacy Service"]
        FE -->|REST| BILL["Billing Service"]
        DSP["External DSPs"] -->|OpenRTB| ADV
    end

    subgraph "Asynchronous (Kafka)"
        ING["Ingestor<br/>(Go)"] -->|raw.fingerprints| KFK["Kafka"]
        KFK -->|raw.fingerprints| IDX["Indexer<br/>(Rust)"]
        KFK -->|raw.fingerprints| MAT["Matcher<br/>(Faust)"]
        MAT -->|matched.viewership| KFK
        KFK -->|matched.viewership| SEG["Segmentation<br/>Engine"]
        SEG -->|audience.segments| KFK
        PRIV -->|consent.events| KFK
    end

    subgraph "Data Stores"
        IDX -->|write| SCY["ScyllaDB"]
        MAT -->|read| SCY
        ADV -->|read/write| PG["PostgreSQL"]
        PRIV -->|read/write| PG
        BILL -->|read/write| PG
        SEG -->|read/write| RED["Redis"]
        ADV -->|read| RED
        ING -->|dedup check| RED
    end
```

### Service Design Targets

| Service | Language | Latency target (p99) | Throughput target | Scaling |
|---|---|---|---|---|
| Fingerprint Ingestor | Go | Tens of ms | Hundreds of thousands of FP/sec | Horizontally scaled HTTP workers |
| Fingerprint Indexer | Rust | Low tens of ms (writes) | Hundreds of thousands of ops/sec | Kubernetes pods |
| Matching Engine | Python (Faust) | Low hundreds of ms | Hundreds of thousands of FP/sec | Kubernetes pods, partitioned by device |
| Segmentation Engine | Python | Seconds (micro-batch) | Hundreds of thousands of events/sec | Kubernetes pods |
| Advertiser API | Python (FastAPI) | Single-digit ms on RTB path | Low tens of thousands req/sec | Kubernetes pods, read-from-cache |
| Privacy Service | Python (FastAPI) | Hundreds of ms | Thousands of req/sec | Kubernetes pods |
| Billing Service | Python (FastAPI) | Seconds (batch) | Low hundreds of req/sec | Kubernetes pods, warehouse-backed |

---

## Privacy Architecture: Compliance by Design

Privacy is a foundational design constraint. Every architectural decision runs through a privacy filter first.

### Privacy Data Flow

```mermaid
graph TB
    subgraph "On Device"
        RAW["Raw Audio<br/>(short window)"] -->|FFT hash| FP["256-bit<br/>Fingerprint Hash"]
        RAW -.->|"NEVER leaves<br/>the device"| X1["Discarded<br/>immediately"]
        HW["Hardware IDs<br/>(MAC, serial)"] -->|"SHA-256 +<br/>monthly salt"| ANON["Anonymized<br/>Device ID"]
        IP["Full IP<br/>Address"] -->|"Truncate to /24"| PFX["IP Prefix"]
        TS["Precise<br/>Timestamp"] -->|"Round to minute"| RTS["Rounded<br/>Timestamp"]
    end

    subgraph "Transmitted to Cloud"
        FP --> PAYLOAD["Payload"]
        ANON --> PAYLOAD
        PFX --> PAYLOAD
        RTS --> PAYLOAD
    end

    subgraph "Never Collected"
        NC1["Raw audio"]
        NC2["Full IP address"]
        NC3["MAC address"]
        NC4["PII / names"]
        NC5["Location (GPS)"]
    end
```

### Consent & Compliance Flow

```mermaid
sequenceDiagram
    participant User as TV User
    participant SDK as ACR SDK
    participant PRIV as Privacy Service
    participant REDIS as Redis (Opt-out Set)
    participant ING as Ingestor
    participant ICE as Data Warehouse

    Note over User: User opts out via TV settings

    User->>SDK: acr_set_consent(false)
    SDK->>SDK: Purge local SQLite cache
    SDK->>SDK: Stop audio capture immediately
    SDK->>PRIV: POST /api/v1/consents (opted_out=true)
    PRIV->>PRIV: Record in PostgreSQL audit log
    PRIV->>REDIS: Add device_id to opt-out set
    PRIV->>PRIV: Publish consent.events to Kafka

    Note over ING: Subsequent fingerprints from this device...
    ING->>REDIS: Check opt-out set
    REDIS-->>ING: BLOCKED - device opted out
    ING->>ING: Drop fingerprint, return 204

    Note over User: User exercises GDPR right to deletion
    User->>PRIV: POST /api/v1/users/{id}/forget-me
    PRIV->>ICE: Batch delete all historical data
    PRIV->>PRIV: Log deletion in immutable audit trail
    PRIV-->>User: Confirmation: all data erased
```

### Regulatory Compliance Matrix

| Regulation | Requirement | Design Approach |
|---|---|---|
| **GDPR** (EU) | Right to access | Privacy service exports all user data from the warehouse |
| **GDPR** (EU) | Right to deletion | Batch delete via Iceberg ACID transactions |
| **GDPR** (EU) | Data minimization | No raw audio, no PII, truncated IPs, rounded timestamps |
| **CCPA** (California) | Opt-out of sale | Redis opt-out set checked at ingestion; immediate enforcement |
| **CCPA** (California) | Disclosure | OpenAPI docs enumerate all collected data fields |
| **PIPEDA** (Canada) | Meaningful consent | SDK requires explicit opt-in before first capture |
| **TCF 2.0** (IAB) | Vendor consent | Privacy service parses TC strings, enforces per-vendor rules |
| **COPPA** (Children) | Age verification | Partner responsible; SDK provides age-gate callback |

These rows describe the *design* for compliance. Real-world certification and legal opinion for each jurisdiction remain the responsibility of the platform operator.

---

## Data Pipeline Architecture

Beyond the real-time streaming layer, Synora runs batch pipelines for analytics, data quality, and operational tasks.

### Pipeline Orchestration

```mermaid
graph TD
    subgraph "Apache Airflow (Orchestrator)"
        DAG1["Nightly Segmentation"]
        DAG2["Data Retention Cleanup"]
        DAG3["Partner Payouts"]
        DAG4["SDK Health Check"]
        DAG5["Data Quality Checks"]
        DAG6["Fingerprint Backfill"]
    end

    subgraph "Stream Processing (Flink)"
        F1["ViewershipIngestionJob<br/>Enriches raw events"]
        F2["HouseholdEnricher<br/>Adds demographic data"]
        F3["IcebergSinkBuilder<br/>Writes to data lake"]
    end

    subgraph "Batch Processing (Spark)"
        S1["HouseholdAggregationJob"]
        S2["RetentionCleanupJob"]
        S3["IcebergMaintenanceJob"]
    end

    subgraph "Data Stores"
        KAFKA["Kafka Topics"]
        S3DB["Data Lake<br/>(Iceberg on object storage)"]
        TRINO["Trino<br/>(Query Engine)"]
    end

    DAG1 --> S1
    DAG2 --> S2
    DAG3 --> TRINO
    DAG4 --> KAFKA
    DAG5 --> TRINO
    DAG6 --> F1

    F1 --> F2 --> F3 --> S3DB
    S1 --> S3DB
    S2 --> S3DB
    S3 --> S3DB
    TRINO --> S3DB
```

### Key Pipeline Jobs

**Nightly segmentation (Spark)** recomputes household-level audience segments by aggregating the previous 24 hours of matched viewership. It catches transitions the real-time engine missed and ensures segment state is consistent for downstream billing.

**Data retention cleanup (Spark)** enforces TTL policies: raw fingerprints beyond the retention window, matched viewership beyond a longer retention window, and aggregated segments beyond a multi-year window are purged from Iceberg using ACID delete transactions.

**Partner payouts (Airflow + Trino)** runs on a monthly cadence, queries the warehouse for all matched viewership attributed to each partner, computes revenue shares, and triggers invoicing.

**Data quality checks (Airflow + Trino)** validates completeness, watches for anomalies in fingerprint match rates, and alerts when any partner's devices show unexpected drops in data volume.

---

## Infrastructure & Deployment

### Cloud Infrastructure

```mermaid
graph TB
    subgraph "Cloud Region"
        subgraph "AZ-1"
            EKS1["Kubernetes Node Group"]
            SCYLLA1["ScyllaDB Node"]
            KAFKA1["Kafka Broker"]
        end

        subgraph "AZ-2"
            EKS2["Kubernetes Node Group"]
            SCYLLA2["ScyllaDB Node"]
            KAFKA2["Kafka Broker"]
        end

        subgraph "AZ-3"
            EKS3["Kubernetes Node Group"]
            SCYLLA3["ScyllaDB Node"]
            KAFKA3["Kafka Broker"]
        end

        subgraph "Managed Services"
            RDS["Managed PostgreSQL<br/>(Multi-AZ)"]
            ELAST["Managed Redis<br/>(Cluster Mode)"]
            S3["Object Store<br/>(Cross-region replication)"]
            ALB["Application<br/>Load Balancer"]
        end
    end

    ALB --> EKS1
    ALB --> EKS2
    ALB --> EKS3
```

### Deployment Pipeline

```mermaid
graph LR
    DEV["Developer<br/>Push"] --> GH["CI<br/>(GitHub Actions)"]

    GH --> LINT["Lint &<br/>Type Check"]
    GH --> TEST["Unit &<br/>Integration Tests"]
    GH --> SEC["Security<br/>Scan"]

    LINT --> BUILD["Container<br/>Build"]
    TEST --> BUILD
    SEC --> BUILD

    BUILD --> STG["Deploy to<br/>Staging"]
    STG --> INTG["Integration<br/>Tests"]
    INTG --> PROD["Deploy to<br/>Production"]
    PROD --> MON["Monitoring<br/>& Alerts"]
```

### Infrastructure Modules

The infrastructure is codified as a set of Terraform modules:

| Module | Resources | Purpose |
|---|---|---|
| **Kubernetes** | Cluster, node groups, IAM roles | Runs all microservices |
| **PostgreSQL** | Multi-AZ managed instance, parameter groups, backups | Consent, billing, advertiser data |
| **Object Storage** | Buckets, lifecycle policies, replication rules | Data lake, audit logs, backups |
| **Kafka** | Brokers, topics, security groups | Event streaming backbone |
| **Redis** | Cluster, parameter groups | Caching, opt-out set, segment lookup |

---

## Observability & Reliability

### Monitoring Stack

```mermaid
graph TB
    subgraph "Services"
        S1["Ingestor"]
        S2["Matcher"]
        S3["Indexer"]
        S4["Segmentation"]
        S5["Advertiser API"]
        S6["Privacy Service"]
        S7["Billing Service"]
    end

    subgraph "Metrics (Prometheus)"
        PROM["Prometheus"]
        M1["fingerprints_ingested_total"]
        M2["matches_found_total"]
        M3["api_requests_duration_seconds"]
        M4["kafka_consumer_lag"]
        M5["scylla_query_latency_p99"]
    end

    subgraph "Visualization (Grafana)"
        GRAF["Grafana"]
        D1["System Overview"]
        D2["Service Health"]
        D3["Pipeline Metrics"]
        D4["Revenue Dashboard"]
    end

    subgraph "Tracing (Jaeger)"
        JAEG["Jaeger"]
        T1["Cross-service<br/>request tracing"]
    end

    S1 & S2 & S3 & S4 & S5 & S6 & S7 -->|"/metrics"| PROM
    PROM --> GRAF
    S1 & S2 & S3 & S4 & S5 & S6 & S7 -->|"trace spans"| JAEG
    GRAF --> D1 & D2 & D3 & D4
    PROM --> M1 & M2 & M3 & M4 & M5
```

### Disaster Recovery Design

| Component | Backup | Frequency | RTO target | RPO target |
|---|---|---|---|---|
| ScyllaDB | Snapshots to object storage | Daily | Hours | 24 hours |
| PostgreSQL | Binary replication | Continuous | Minutes | ~0 |
| Kafka | Replication factor 3 | Real-time | 0 | 0 |
| Data Lake | Cross-region replication | Continuous | 0 | 0 |
| Redis | Rebuildable | N/A | Minutes | N/A |

---

## Scaling

Synora is designed to scale horizontally at every layer. As device footprint grows, the pattern is to add capacity — never to rewrite.

### Scaling Trajectory

```mermaid
graph LR
    subgraph "Phase 1: Launch"
        P1["Small device footprint<br/>Modest cluster sizes"]
    end

    subgraph "Phase 2: Growth"
        P2["Mid device footprint<br/>Wider Kafka / ScyllaDB"]
    end

    subgraph "Phase 3: Scale"
        P3["Large device footprint<br/>Sharded topics,<br/>Multi-region option"]
    end

    subgraph "Phase 4: Global"
        P4["Global device footprint<br/>Federated Kafka,<br/>Multi-region ScyllaDB"]
    end

    P1 --> P2 --> P3 --> P4
```

Every component is independently scalable: Kafka brokers join with zero downtime (automatic rebalance), ScyllaDB nodes join the ring with streaming rebalance (no locks), and Kubernetes services auto-scale on CPU utilization and Kafka consumer lag.

---

## Defensibility

The hard parts of an ACR platform are not the algorithms — those are well understood in the literature. The things that compound slowly and are hard to replicate:

**Device footprint.** More integrated devices means richer signal. Richer signal supports finer segments. Finer segments attract advertiser demand. Demand funds partner revenue share, which attracts more integrations. Getting this wheel spinning is the main business problem.

**Reference content database.** A usable reference index requires continuous ingestion of broadcast and streaming content and careful management of licensing. A new entrant cannot match a single fingerprint without this corpus.

**Privacy and compliance infrastructure.** Consent management, audit logs, GDPR/CCPA deletion workflows, and TCF 2.0 integration represent real engineering and legal work. Getting this wrong produces regulatory exposure that no OEM partner will accept.

**Partner integration inertia.** Once a partner has embedded the SDK in firmware, validated it through QA, and started receiving revenue, the switching cost is high. Firmware updates on smart TVs are slow and risky.

---

## Getting Started

### For Developers

```bash
# Clone the repo
git clone https://github.com/synora/acraas.git
cd acraas

# Start the full platform locally
cp .env.example .env
docker-compose up -d
./docker-compose.init.sh

# Access the services
open http://localhost:3000     # Advertiser dashboard
open http://localhost:3001     # Grafana (admin/admin)
open http://localhost:8089     # Airflow
```

See `docs/sdk-integration-guide.md` for SDK integration, `docs/ARCHITECTURE.md` for the full system design, and `docs/api-reference.md` for the platform API.

### For Partners

The partner onboarding flow has four stages: integration agreement, SDK integration into firmware, QA validation against the integration test suite, and OTA rollout to an installed base. Ongoing payouts are handled through the billing service against a configurable revenue-share split.

### For Advertisers

The advertiser flow has three stages: account creation and API key provisioning, segment definition through the dashboard or segment-builder DSL, and OpenRTB integration with the demand-side platforms of choice. Delivery reporting is surfaced in the dashboard.

---

## Roadmap

Synora's present scope is fingerprint capture, matching, segmentation, and monetization. Areas the architecture extends naturally into:

**Cross-device graph.** Linking TV viewership to mobile and desktop behavior through probabilistic device graphs, enabling cross-screen attribution.

**Content-level insights.** Moving beyond *what show* to *what scene* and *what ad* recognition, enabling competitive ad intelligence and creative optimization.

**International expansion.** Adapting the platform for jurisdictions with stricter or region-specific privacy frameworks and content databases.

**ML-powered segmentation.** Replacing rule-based segments with learned models that discover high-value audience clusters automatically.

**Real-time attribution.** Closing the loop between TV ad exposure and downstream behavior.

---
