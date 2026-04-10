# Fingerprint Indexer Service

A Rust async service that maintains the reference fingerprint database in ScyllaDB with hamming distance-based fuzzy matching via LSH (Locality Sensitive Hashing).

## Features

- ScyllaDB-backed fingerprint storage with automatic keyspace/table initialization
- LSH-based hamming distance matching (8 bands x 32-bit for sub-5ms lookups)
- Kafka consumer for automatic reference indexing from `reference.content` topic
- Axum-based HTTP API with structured logging
- Token-aware load balancing with DC awareness
- Batch insertion for throughput optimization

## HTTP API

### Health Check
```bash
GET /health
```

### Index Fingerprint
```bash
POST /v1/fingerprints/index
Content-Type: application/json

{
  "fingerprint_hash": "a1b2c3d4...",
  "content_id": "content-123",
  "title": "Breaking Bad",
  "network": "AMC",
  "episode": "Season 1 Episode 1",
  "airdate": "2008-01-20T00:00:00Z",
  "genre": "Drama",
  "confidence": 0.98
}
```

### Lookup Fingerprint
```bash
POST /v1/fingerprints/lookup
Content-Type: application/json

{
  "fingerprint_hash": "a1b2c3d4...",
  "hamming_tolerance": 8
}
```

Response:
```json
{
  "matched": true,
  "fingerprint": {
    "fingerprint_hash": "a1b2c3d4...",
    "content_id": "content-123",
    "title": "Breaking Bad",
    ...
  },
  "hamming_distance": 3,
  "lookup_time_ms": 2.45
}
```

### Get Statistics
```bash
GET /v1/fingerprints/stats
```

Response:
```json
{
  "total_fingerprints": 10000,
  "by_network": {
    "AMC": 2500,
    "HBO": 3200,
    ...
  }
}
```

## Configuration

Environment variables:

- `SCYLLA_HOSTS` - Comma-separated ScyllaDB hosts (default: `127.0.0.1:9042`)
- `KAFKA_BOOTSTRAP` - Kafka bootstrap servers (default: `kafka:9092`)
- `KAFKA_GROUP` - Kafka consumer group (default: `fingerprint-indexer-group`)
- `HTTP_PORT` - HTTP server port (default: `8080`)
- `BATCH_SIZE` - Kafka batch size (default: `100`)
- `REPLICATION_FACTOR` - ScyllaDB replication (default: `1`)
- `HAMMING_THRESHOLD` - Max hamming distance for matches (default: `8`)
- `RUST_LOG` - Log level filter

## Building

```bash
cargo build --release
```

## Running

Local development (requires ScyllaDB and Kafka):
```bash
cargo run
```

Docker:
```bash
docker build -t fingerprint-indexer:latest .
docker run -p 8080:8080 \
  -e SCYLLA_HOSTS=scylla:9042 \
  -e KAFKA_BOOTSTRAP=kafka:9092 \
  fingerprint-indexer:latest
```

## Database Schema

### Tables

**acraas.reference_fingerprints** - Primary fingerprint storage
```sql
CREATE TABLE IF NOT EXISTS acraas.reference_fingerprints (
    fingerprint_hash text PRIMARY KEY,
    content_id text,
    title text,
    network text,
    episode text,
    airdate timestamp,
    genre text,
    created_at timestamp,
    confidence float
);
```

**acraas.fingerprint_bands** - LSH band index for hamming distance
```sql
CREATE TABLE IF NOT EXISTS acraas.fingerprint_bands (
    band_index int,
    band_hash text,
    fingerprint_hash text,
    PRIMARY KEY ((band_index, band_hash), fingerprint_hash)
);
```

## Performance

- Hamming distance lookup: <5ms (99th percentile)
- Batch insert: 100 fingerprints in ~200ms
- Supports 10k+ indexed fingerprints with sub-5ms lookups
- Connection pooling with token-aware load balancing
