#\!/bin/bash

set -e

echo "ACRaaS Quick Start"
echo "=================="
echo ""

if [ \! -f .env ]; then
  echo "Creating .env from .env.example..."
  cp .env.example .env
fi

echo "Building Docker images..."
docker-compose build

echo ""
echo "Starting services..."
docker-compose up -d

echo ""
echo "Waiting for services to be healthy..."
sleep 10

echo "Initializing databases..."
chmod +x docker-compose.init.sh
./docker-compose.init.sh

echo ""
echo "✓ ACRaaS is ready\!"
echo ""
echo "Service URLs:"
echo "  Frontend:        http://localhost:3000"
echo "  Advertiser API:  http://localhost:8084"
echo "  Grafana:         http://localhost:3001 (admin/admin)"
echo "  Prometheus:      http://localhost:9090"
echo "  Jaeger:          http://localhost:16686"
echo "  Airflow:         http://localhost:8089"
echo "  Kafka UI:        http://localhost:8080"
echo ""
echo "Run health checks with: ./health-check.sh"
