# Fingerprint Ingestor - Synora

High-throughput HTTP fingerprint ingestion service for Synora. Receives fingerprint batches from TV SDK devices and publishes them to Kafka for downstream processing.

**Target Throughput:** 500K requests/sec  
**Language:** Go 1.22  
**Framework:** valyala/fasthttp  
**Message Queue:** Apache Kafka  
**Cache/State:** Redis  

## Architecture

```
TV SDK Devices
    ↓
[HTTP POST /v1/fingerprints]
    ↓
Fingerprint Ingestor
├─ Authentication (X-API-Key)
├─ Rate Limiting (Redis, 10K req/sec per key)
├─ Validation (format, timestamp, IP)
├─ GeoIP Filtering (reject datacenter IPs)
├─ Kafka Publishing (raw.fingerprints topic)
└─ Prometheus Metrics (:9090)
    ↓
Apache Kafka (raw.fingerprints topic)
    ↓
Downstream Services (Stream Processing, Analytics)
```

## Features

- **High Performance:** Uses fasthttp (10x faster than net/http), supports 100K concurrent connections
- **Fire-and-Forget:** Returns 202 Accepted immediately after validation
- **Async Kafka Publishing:** Non-blocking message publishing with error monitoring
- **Rate Limiting:** Redis-backed sliding window rate limiter (10K req/sec per API key)
- **GeoIP Filtering:** Rejects IPs from datacenters, Tor exit nodes using MaxMind GeoIP2
- **Comprehensive Validation:** Device ID, fingerprint hash, timestamp, batch size checks
- **Prometheus Metrics:** Full observability with histogram, counter, and gauge metrics
- **Graceful Shutdown:** Flushes pending Kafka messages on termination
- **Production-Ready:** Structured logging with zap, error handling, health checks

## Quick Start

### Prerequisites

- Go 1.22+
- Docker & Docker Compose (optional, for containerized setup)
- Kafka broker
- Redis instance
- (Optional) MaxMind GeoIP2 ASN database

### Environment Setup

```bash
# Copy example config
cp .env.example .env

# Edit as needed
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
REDIS_URL=redis://localhost:6379
```

### Local Development

```bash
# Install dependencies
go mod download

# Run with hot-reload (requires air)
make run

# Or build and run manually
go build -o bin/fingerprint-ingestor main.go
./bin/fingerprint-ingestor
```

### Docker Compose Stack

```bash
# Start full stack (Kafka, Redis, Ingestor)
make docker-up

# View logs
make docker-logs

# Stop stack
make docker-down
```

### Build Production Image

```bash
make docker-build

# Run
docker run -p 8080:8080 -p 9090:9090 \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  -e REDIS_URL=redis://redis:6379 \
  acraas/fingerprint-ingestor:latest
```

## API Usage

### POST /v1/fingerprints

Accept fingerprint batch for ingestion.

**Request:**
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

**Response (202 Accepted):**
```json
{
  "status": "accepted",
  "processed": 1,
  "rejected": 0
}
```

See [API.md](API.md) for full endpoint documentation.

### GET /health

Health check endpoint.

```bash
curl http://localhost:8080/health
```

### GET /metrics

Prometheus metrics (exposed on separate port :9090).

```bash
curl http://localhost:9090/metrics
```

## Project Structure

```
fingerprint-ingestor/
├── main.go                 # Entry point, server setup, routing
├── config/
│   └── config.go          # Configuration loading from environment
├── handler/
│   ├── ingest.go          # POST /v1/fingerprints handler
│   └── health.go          # GET /health and /metrics handlers
├── middleware/
│   └── auth.go            # X-API-Key authentication
├── kafka/
│   └── producer.go        # Kafka producer wrapper
├── ratelimit/
│   └── redis.go           # Redis sliding window rate limiter
├── geoip/
│   └── filter.go          # MaxMind GeoIP filtering
├── metrics/
│   └── prometheus.go      # Prometheus metric definitions
├── tests/
│   └── ingest_test.go     # Integration tests and benchmarks
├── docker-compose.yml     # Local dev stack
├── Dockerfile             # Production multi-stage build
├── Dockerfile.dev         # Development with hot-reload
├── .air.toml              # Hot-reload configuration
├── Makefile               # Build and development targets
├── go.mod & go.sum        # Dependency management
└── API.md                 # API documentation
```

## Configuration

All configuration is via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LISTEN_ADDR` | `:8080` | HTTP server listen address |
| `METRICS_LISTEN_ADDR` | `:9090` | Prometheus metrics listen address |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker addresses |
| `KAFKA_TOPIC` | `raw.fingerprints` | Kafka topic for fingerprints |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `RATE_LIMIT_PER_SECOND` | `10000` | Requests per second per API key |
| `MAX_BATCH_SIZE` | `100` | Maximum fingerprints per batch |
| `TIMESTAMP_TOLERANCE_SEC` | `300` | Timestamp age tolerance (5 min) |
| `MAXMIND_DB_PATH` | `/etc/geoip/GeoLite2-ASN.mmdb` | Path to GeoIP database |

## Validation Rules

- **Device ID:** 64-char hex string (SHA-256)
- **Fingerprint Hash:** 64-char hex string
- **Timestamp:** Within 5 minutes of server time (milliseconds)
- **IP Address:** Not from datacenter (AWS, GCP, Azure, etc.) or Tor exit nodes
- **Batch Size:** 1-100 fingerprints per request

Invalid events are silently discarded, but batch is still accepted (202).

## Metrics

Prometheus metrics available at `/metrics`:

- `acraas_ingest_requests_total` - Total requests by status and manufacturer
- `acraas_ingest_request_duration_seconds` - Request latency histogram
- `acraas_ingest_batch_size` - Fingerprints per batch histogram
- `acraas_kafka_publish_errors_total` - Kafka publishing errors
- `acraas_kafka_messages_published_total` - Successfully published messages
- `acraas_ratelimit_rejections_total` - Rate limit rejections per API key
- `acraas_geoip_rejections_total` - GeoIP filter rejections
- `acraas_validation_errors_total` - Validation errors by type
- `acraas_auth_errors_total` - Auth errors by type

## Testing

```bash
# Run unit tests
go test -v ./...

# Run with coverage
go test -cover ./...

# Run benchmarks
go test -bench=. -benchmem ./tests/...

# Run in Docker
make docker-test
```

## Performance Tuning

The service is optimized for 500K req/sec throughput:

- **fasthttp:** Low-allocation HTTP library, 10x faster than net/http
- **Max Connections:** 100,000 (configurable in main.go)
- **Concurrency:** 1,000,000 goroutine budget
- **Kafka Batching:** 5ms linger time + snappy compression
- **Rate Limiter:** O(1) Redis operations per request
- **GeoIP Cache:** 1-hour in-memory cache with sync.Map

For further optimization:
1. Tune OS limits: `ulimit -n 300000`
2. Tune kernel: net.core.somaxconn, net.ipv4.tcp_max_syn_backlog
3. Use `GOMAXPROCS` to pin to CPU cores
4. Enable kernel bypass networking (if available)

## Deployment

### Kubernetes

```yaml
apiVersion: v1
kind: Service
metadata:
  name: fingerprint-ingestor
spec:
  type: LoadBalancer
  ports:
    - port: 80
      targetPort: 8080
      name: http
    - port: 9090
      targetPort: 9090
      name: metrics
  selector:
    app: fingerprint-ingestor
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fingerprint-ingestor
spec:
  replicas: 10  # Adjust for target throughput
  selector:
    matchLabels:
      app: fingerprint-ingestor
  template:
    metadata:
      labels:
        app: fingerprint-ingestor
    spec:
      containers:
      - name: fingerprint-ingestor
        image: acraas/fingerprint-ingestor:latest
        ports:
        - containerPort: 8080
        - containerPort: 9090
        env:
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: "kafka:9092"
        - name: REDIS_URL
          value: "redis://redis:6379"
        resources:
          requests:
            cpu: 500m
            memory: 256Mi
          limits:
            cpu: 2
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Docker Swarm

```bash
docker service create \
  --name fingerprint-ingestor \
  --publish 8080:8080 \
  --publish 9090:9090 \
  --env KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  --env REDIS_URL=redis://redis:6379 \
  --replicas 10 \
  acraas/fingerprint-ingestor:latest
```

## Troubleshooting

### High Memory Usage
- Check Kafka producer queue: may indicate slow brokers
- Monitor Redis connection pool
- Check rate limiter key cardinality

### High Error Rate
- Check Kafka broker connectivity: `telnet kafka 9092`
- Check Redis connectivity: `redis-cli PING`
- Review application logs for validation errors
- Check GeoIP database path if present

### Rate Limit Rejections
- Verify Redis is running and accessible
- Check rate limit configuration (default 10K req/sec)
- Monitor key cardinality (too many API keys = too many Redis keys)

### Slow Response Times
- Check Kafka broker performance
- Monitor system CPU and memory
- Review Prometheus metrics for bottlenecks
- Consider horizontal scaling

## Dependencies

Production dependencies:
- `github.com/valyala/fasthttp` - HTTP library
- `github.com/confluentinc/confluent-kafka-go/v2` - Kafka client
- `github.com/go-redis/redis/v9` - Redis client
- `github.com/oschwald/geoip2-golang` - GeoIP lookup
- `github.com/prometheus/client_golang` - Prometheus metrics
- `github.com/caarlos0/env/v10` - Configuration loading
- `go.uber.org/zap` - Logging

Development dependencies:
- `github.com/cosmtrek/air` - Hot-reload

## License

MIT License - See LICENSE file

## Support

For issues or questions:
1. Check [API.md](API.md) for endpoint documentation
2. Review logs: `docker-compose logs fingerprint-ingestor`
3. Check metrics: `curl http://localhost:9090/metrics`
4. Verify dependencies: `go mod tidy && go mod verify`
