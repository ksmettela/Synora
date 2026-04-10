.PHONY: help build test run clean docker-build docker-up docker-down lint fmt

help:
	@echo "Fingerprint Ingestor - Available targets:"
	@echo "  build          - Build the application binary"
	@echo "  test           - Run unit tests"
	@echo "  bench          - Run benchmarks"
	@echo "  run            - Run the application locally"
	@echo "  lint           - Run linter"
	@echo "  fmt            - Format code"
	@echo "  clean          - Clean build artifacts"
	@echo "  docker-build   - Build Docker image"
	@echo "  docker-up      - Start Docker Compose stack"
	@echo "  docker-down    - Stop Docker Compose stack"
	@echo "  docker-logs    - View Docker logs"

build:
	@echo "Building fingerprint-ingestor..."
	go build -o bin/fingerprint-ingestor main.go

test:
	@echo "Running tests..."
	go test -v ./...

bench:
	@echo "Running benchmarks..."
	go test -bench=. -benchmem ./tests/...

run: build
	@echo "Starting fingerprint-ingestor..."
	./bin/fingerprint-ingestor

lint:
	@echo "Running golangci-lint..."
	golangci-lint run ./...

fmt:
	@echo "Formatting code..."
	go fmt ./...
	goimports -w .

clean:
	@echo "Cleaning build artifacts..."
	rm -rf bin/ tmp/ dist/
	go clean

docker-build:
	@echo "Building Docker image..."
	docker build -t acraas/fingerprint-ingestor:latest .

docker-dev-build:
	@echo "Building dev Docker image..."
	docker build -f Dockerfile.dev -t acraas/fingerprint-ingestor:dev .

docker-up:
	@echo "Starting Docker Compose stack..."
	docker-compose up -d

docker-down:
	@echo "Stopping Docker Compose stack..."
	docker-compose down

docker-logs:
	@echo "Showing Docker logs..."
	docker-compose logs -f fingerprint-ingestor

docker-test:
	@echo "Testing in Docker..."
	docker-compose run --rm fingerprint-ingestor go test -v ./...

mod-tidy:
	@echo "Tidying dependencies..."
	go mod tidy

mod-download:
	@echo "Downloading dependencies..."
	go mod download

version:
	@go version
	@echo "Module: $$(go list -m)"
