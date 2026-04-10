# Fingerprint Ingestor API Documentation

## Overview

High-throughput HTTP fingerprint ingestion service for ACRaaS. Accepts fingerprint batches from TV SDK devices and publishes them to Kafka for processing. Target throughput: 500K requests/sec.

## Endpoints

### POST /v1/fingerprints

Accepts a batch of fingerprints and publishes them to Kafka.

**Authentication**: Required (`X-API-Key` header)

**Request**:
```json
{
  "batch": [
    {
      "device_id": "a0000000000000000000000000000000000000000000000000000000000000",
      "fingerprint_hash": "b1111111111111111111111111111111111111111111111111111111111111",
      "timestamp_utc": 1712748932000,
      "manufacturer": "LG",
      "model": "OLED55C3",
      "ip_address": "192.168.1.100"
    }
  ]
}
```

**Request Headers**:
- `X-API-Key`: API key for authentication (required)
- `Content-Type`: application/json (required)

**Parameters**:
- `batch` (array, required): Array of fingerprint events (max 100 items)

**Fingerprint Event Fields**:
- `device_id` (string, required): SHA-256 hash of device ID as 64-char hex string
- `fingerprint_hash` (string, required): Device fingerprint hash as 64-char hex string
- `timestamp_utc` (integer, required): Event timestamp in milliseconds (must be within 5 minutes of now)
- `manufacturer` (string, required): Device manufacturer (e.g., "LG", "Samsung")
- `model` (string, required): Device model (e.g., "OLED55C3")
- `ip_address` (string, required): Client IP address (will be rejected if from datacenter)

**Response (202 Accepted)**:
```json
{
  "status": "accepted",
  "processed": 95,
  "rejected": 5
}
```

**Status Codes**:
- `202 Accepted`: Batch accepted for processing (fire-and-forget)
- `400 Bad Request`: Invalid request format or validation error
  - Invalid JSON body
  - Batch size exceeds limit (>100 items)
  - Invalid device_id or fingerprint_hash format
  - Timestamp out of range
- `401 Unauthorized`: Missing X-API-Key header
- `403 Forbidden`: Invalid or revoked API key
- `429 Too Many Requests`: Rate limit exceeded (10K req/sec per API key)
- `500 Internal Server Error`: Server error

### GET /health

Health check endpoint.

**Response (200 OK)**:
```json
{
  "status": "ok",
  "kafka": "ok",
  "redis": "ok",
  "time": "2024-04-10T12:34:56Z"
}
```

**Status Codes**:
- `200 OK`: All systems operational
- `503 Service Unavailable`: One or more dependencies down
  - status will be "degraded"

### GET /metrics

Prometheus metrics endpoint.

**Content-Type**: text/plain

**Metrics Exposed**:
- `acraas_ingest_requests_total`: Total ingestion requests (counter)
- `acraas_ingest_request_duration_seconds`: Request processing duration (histogram)
- `acraas_ingest_batch_size`: Fingerprints per batch (histogram)
- `acraas_kafka_publish_errors_total`: Kafka publishing errors (counter)
- `acraas_kafka_messages_published_total`: Successfully published messages (counter)
- `acraas_ratelimit_rejections_total`: Rate limit rejections (counter)
- `acraas_geoip_rejections_total`: GeoIP filter rejections (counter)
- `acraas_validation_errors_total`: Validation errors by type (counter)
- `acraas_auth_errors_total`: Auth errors by type (counter)

## Validation Rules

### Device ID Format
- Must be 64-character hexadecimal string (0-9, a-f, A-F)
- Pattern: `^[a-fA-F0-9]{64}$`

### Fingerprint Hash Format
- Must be 64-character hexadecimal string (0-9, a-f, A-F)
- Pattern: `^[a-fA-F0-9]{64}$`

### Timestamp Validation
- Must be within 300 seconds (5 minutes) of server time
- Supports both past (up to 5 minutes old) and future timestamps (up to 5 minutes ahead)
- Unit: milliseconds (UNIX epoch * 1000)

### IP Address Filtering
- Rejects IPs from known datacenters (AWS, GCP, Azure, DigitalOcean, Linode, etc.)
- Rejects Tor exit node IPs
- Allows private IP ranges (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- Requires MaxMind GeoIP2 database (gracefully degrades if unavailable)

### Batch Size
- Minimum: 1 fingerprint per batch
- Maximum: 100 fingerprints per batch (configurable)

### Rate Limiting
- Per API key sliding window
- Default: 10,000 requests per second
- Window: 1 second
- Uses Redis for distributed state

## Error Handling

### Validation Errors
Individual fingerprints that fail validation are silently discarded:
- Invalid device_id format
- Invalid fingerprint_hash format
- Timestamp out of range
- IP address from datacenter/Tor

The batch is still accepted (202), but rejected items are counted in the response and logged.

### Rate Limiting
When rate limit is exceeded:
- HTTP 429 Too Many Requests
- `Retry-After` header with suggested retry delay (milliseconds)

### Authentication
- Missing API key → HTTP 401 Unauthorized
- Invalid/revoked API key → HTTP 403 Forbidden

## Examples

### Valid Request
```bash
curl -X POST http://localhost:8080/v1/fingerprints \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "batch": [
      {
        "device_id": "a0000000000000000000000000000000000000000000000000000000000000",
        "fingerprint_hash": "b1111111111111111111111111111111111111111111111111111111111111",
        "timestamp_utc": 1712748932000,
        "manufacturer": "LG",
        "model": "OLED55C3",
        "ip_address": "203.0.113.42"
      }
    ]
  }'
```

### Health Check
```bash
curl http://localhost:8080/health
```

### Metrics
```bash
curl http://localhost:9090/metrics
```

## Configuration

See `.env.example` for all available configuration options:

- `LISTEN_ADDR`: HTTP server listen address (default: `:8080`)
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka broker addresses (default: `localhost:9092`)
- `KAFKA_TOPIC`: Kafka topic for fingerprints (default: `raw.fingerprints`)
- `REDIS_URL`: Redis connection string (default: `redis://localhost:6379`)
- `RATE_LIMIT_PER_SECOND`: Requests per second limit (default: `10000`)
- `MAX_BATCH_SIZE`: Maximum fingerprints per batch (default: `100`)
- `TIMESTAMP_TOLERANCE_SEC`: Timestamp age tolerance (default: `300`)
- `METRICS_LISTEN_ADDR`: Prometheus metrics listen address (default: `:9090`)
- `MAXMIND_DB_PATH`: Path to MaxMind GeoIP2 database

## Kafka Schema

Fingerprints are published to Kafka as JSON with the following schema:

```json
{
  "type": "record",
  "name": "RawFingerprint",
  "namespace": "com.synora.acraas",
  "fields": [
    {"name": "device_id", "type": "string"},
    {"name": "fingerprint_hash", "type": "string"},
    {"name": "timestamp_utc", "type": "long"},
    {"name": "manufacturer", "type": "string"},
    {"name": "model", "type": "string"},
    {"name": "ip_address", "type": "string"},
    {"name": "ingested_at", "type": "long"}
  ]
}
```

Partitioning: By `device_id` (hash partitioner)
Compression: Snappy
Acks: All
Retries: 3
Linger: 5ms

## Performance Characteristics

- Target throughput: 500K requests/second
- Max concurrent connections: 100,000
- Concurrency: 1,000,000
- Request timeout: 10 seconds
- Memory efficient: Fire-and-forget pattern
- Low latency: 202 response returned immediately after validation
- Batch processing: Async Kafka publishing with error monitoring

## Monitoring

Use Prometheus metrics endpoint (`/metrics`) to monitor:
- Request rate and latency
- Batch sizes
- Kafka publishing errors
- Rate limit rejections
- GeoIP filtering rejections
- Validation errors by type
