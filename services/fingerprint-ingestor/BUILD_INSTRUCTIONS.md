# Build Instructions - Fingerprint Ingestor

## Build from Source

### Prerequisites
- Go 1.22 or later
- librdkafka development libraries
- Make (optional, but recommended)

### Local Development Build

```bash
cd /Users/kumarswamymettela/Downloads/Side\ Projects/Synora/acraas/services/fingerprint-ingestor/

# Install dependencies
go mod download

# Build binary
go build -o bin/fingerprint-ingestor main.go

# Binary location: ./bin/fingerprint-ingestor
```

### Build with Makefile

```bash
# Build
make build

# Run
make run

# Both in one
make build run
```

### Docker Build

#### Production Image
```bash
# Build production image
docker build -t acraas/fingerprint-ingestor:latest .

# Build with version tag
docker build --build-arg VERSION=1.0.0 -t acraas/fingerprint-ingestor:1.0.0 .

# Build with build timestamp
docker build --build-arg BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
             -t acraas/fingerprint-ingestor:latest .
```

#### Development Image (with hot-reload)
```bash
docker build -f Dockerfile.dev -t acraas/fingerprint-ingestor:dev .

# Run with hot-reload
docker run -it -p 8080:8080 -p 9090:9090 \
           -v $(pwd):/app \
           acraas/fingerprint-ingestor:dev
```

### Docker Compose Build

```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build fingerprint-ingestor

# Build without cache
docker-compose build --no-cache fingerprint-ingestor
```

## Running

### Local Execution

```bash
# With default config
./bin/fingerprint-ingestor

# With custom environment
export LISTEN_ADDR=:8080
export KAFKA_BOOTSTRAP_SERVERS=kafka.example.com:9092
export REDIS_URL=redis://redis.example.com:6379
./bin/fingerprint-ingestor
```

### Docker Container

```bash
# Run production image
docker run -d \
  -p 8080:8080 \
  -p 9090:9090 \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  -e REDIS_URL=redis://redis:6379 \
  --name fingerprint-ingestor \
  acraas/fingerprint-ingestor:latest

# View logs
docker logs -f fingerprint-ingestor

# Stop container
docker stop fingerprint-ingestor
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f fingerprint-ingestor

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Testing

### Unit Tests

```bash
# Run all tests
go test -v ./...

# Run specific package tests
go test -v ./handler/...

# Run with coverage
go test -cover ./...

# Generate coverage report
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out

# Run specific test
go test -v -run TestIngestHappyPath ./tests/...
```

### Integration Tests

```bash
# Run integration tests (requires running services)
go test -v -tags=integration ./tests/...

# Run integration test in Docker
make docker-test
```

### Benchmarks

```bash
# Run all benchmarks
go test -bench=. ./tests/...

# Run specific benchmark
go test -bench=BenchmarkIngest -benchmem ./tests/...

# Generate CPU profile
go test -bench=. -cpuprofile=cpu.prof ./tests/...
go tool pprof cpu.prof

# Generate memory profile
go test -bench=. -memprofile=mem.prof ./tests/...
go tool pprof mem.prof
```

### Load Testing

```bash
# Basic load test (1000 requests, batch of 10, 10 concurrent)
./scripts/load-test.sh 1000 10 10

# Heavy load test (100K requests, batch of 100, 100 concurrent)
./scripts/load-test.sh 100000 100 100

# Custom parameters
NUM_REQUESTS=50000 BATCH_SIZE=50 CONCURRENCY=50 ./scripts/load-test.sh
```

## Code Quality

### Linting

```bash
# Install golangci-lint
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

# Run linter
make lint

# Or directly
golangci-lint run ./...
```

### Formatting

```bash
# Format code
make fmt

# Or directly
go fmt ./...
goimports -w .
```

### Static Analysis

```bash
# Run go vet
go vet ./...

# Check for common mistakes
staticcheck ./...
```

## Dependency Management

### Update Dependencies

```bash
# Check for outdated packages
go outdated

# Update all dependencies
go get -u ./...

# Update specific package
go get -u github.com/valyala/fasthttp

# Tidy up dependencies
make mod-tidy

# Verify dependencies
go mod verify

# Download all dependencies
make mod-download
```

## Deployment Builds

### Multi-Platform Build

```bash
# Linux AMD64
CGO_ENABLED=1 GOOS=linux GOARCH=amd64 \
  go build -o bin/fingerprint-ingestor-linux-amd64 main.go

# Linux ARM64 (for Raspberry Pi, M1 Mac)
CGO_ENABLED=1 GOOS=linux GOARCH=arm64 \
  go build -o bin/fingerprint-ingestor-linux-arm64 main.go

# macOS
CGO_ENABLED=1 GOOS=darwin GOARCH=amd64 \
  go build -o bin/fingerprint-ingestor-darwin-amd64 main.go
```

### Release Build

```bash
# Create release binary with version info
VERSION=1.0.0
BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
COMMIT=$(git rev-parse --short HEAD)

go build \
  -ldflags="-X main.Version=${VERSION} \
            -X main.BuildTime=${BUILD_TIME} \
            -X main.Commit=${COMMIT} \
            -w -s" \
  -o bin/fingerprint-ingestor-${VERSION} \
  main.go
```

### Docker Registry Push

```bash
# Tag image
docker tag acraas/fingerprint-ingestor:latest \
           registry.example.com/acraas/fingerprint-ingestor:1.0.0

# Push to registry
docker push registry.example.com/acraas/fingerprint-ingestor:1.0.0

# Push with multiple tags
docker tag acraas/fingerprint-ingestor:latest \
           registry.example.com/acraas/fingerprint-ingestor:latest
docker push registry.example.com/acraas/fingerprint-ingestor:latest
```

## Troubleshooting Build Issues

### CGO Issues
```bash
# Install dependencies (Ubuntu/Debian)
sudo apt-get install librdkafka-dev

# Install dependencies (macOS)
brew install librdkafka

# Build without CGO (not recommended, some features disabled)
CGO_ENABLED=0 go build main.go
```

### Module Not Found
```bash
# Clean module cache
go clean -modcache

# Re-download dependencies
go mod download

# Update go.sum
go mod tidy
```

### Docker Build Fails
```bash
# Build without cache
docker build --no-cache -t acraas/fingerprint-ingestor:latest .

# Check build logs
docker build -t acraas/fingerprint-ingestor:latest . 2>&1 | head -50

# Verify Dockerfile syntax
docker build --help | grep -i syntax
```

## Build Artifacts

After building, key artifacts are located in:

```
./bin/
  └── fingerprint-ingestor          # Binary executable
     
docker images | grep fingerprint-ingestor  # Docker images
  acraas/fingerprint-ingestor:latest
  acraas/fingerprint-ingestor:dev

coverage.out                          # Test coverage report (after test -cover)
cpu.prof, mem.prof                    # Profiling data (after benchmarks)
```

## Clean Build

```bash
# Clean all build artifacts
make clean

# Remove Go cache
go clean -cache

# Remove modules cache
go clean -modcache

# Full cleanup
make clean && rm -rf bin/ tmp/ dist/ coverage.out *.prof
```

## Next Steps

1. **Build the project**: `make build`
2. **Run tests**: `go test -v ./...`
3. **Start services**: `make docker-up`
4. **Load test**: `./scripts/load-test.sh 1000 10 10`
5. **Check metrics**: `curl http://localhost:9090/metrics`

## Build Checklist

- [ ] Go 1.22+ installed
- [ ] librdkafka development libraries installed
- [ ] Dependencies downloaded: `go mod download`
- [ ] Binary builds: `make build`
- [ ] Tests pass: `go test -v ./...`
- [ ] Linting passes: `make lint`
- [ ] Docker image builds: `make docker-build`
- [ ] Docker Compose starts: `make docker-up`
- [ ] Health check passes: `curl http://localhost:8080/health`
- [ ] Metrics accessible: `curl http://localhost:9090/metrics`

---

For more information, see README.md, API.md, and QUICK_START.md
