#\!/bin/bash

set -e

echo "Synora Health Check"
echo "==================="
echo ""

services=(
  "http://localhost:8080"   "Fingerprint Ingestor"
  "http://localhost:8081"   "Matching Engine"
  "http://localhost:8082"   "Fingerprint Indexer"
  "http://localhost:8083"   "Segmentation Engine"
  "http://localhost:8084"   "Advertiser API"
  "http://localhost:8085"   "Privacy Service"
  "http://localhost:8086"   "Billing Service"
  "http://localhost:3000"   "Frontend"
  "http://localhost:3001"   "Grafana"
  "http://localhost:9090"   "Prometheus"
  "http://localhost:16686"  "Jaeger"
  "http://localhost:8089"   "Airflow"
)

failed=0
for i in "${\!services[@]}"; do
  if [ $((i % 2)) -eq 0 ]; then
    url="${services[$i]}"
    name="${services[$((i+1))]}"
    
    if curl -f "$url" > /dev/null 2>&1; then
      echo "✓ $name ($url)"
    else
      echo "✗ $name ($url)"
      failed=$((failed + 1))
    fi
  fi
done

echo ""
echo "Database Checks"
echo "==============="

# PostgreSQL
if docker exec acraas-postgres pg_isready -U acraas > /dev/null 2>&1; then
  echo "✓ PostgreSQL"
else
  echo "✗ PostgreSQL"
  failed=$((failed + 1))
fi

# ScyllaDB
if docker exec acraas-scylladb cqlsh -e "describe cluster" > /dev/null 2>&1; then
  echo "✓ ScyllaDB"
else
  echo "✗ ScyllaDB"
  failed=$((failed + 1))
fi

# Redis
if docker exec acraas-redis redis-cli -a redispass123 ping > /dev/null 2>&1; then
  echo "✓ Redis"
else
  echo "✗ Redis"
  failed=$((failed + 1))
fi

# Kafka
if docker exec acraas-kafka kafka-topics.sh --bootstrap-server localhost:9092 --list > /dev/null 2>&1; then
  echo "✓ Kafka"
else
  echo "✗ Kafka"
  failed=$((failed + 1))
fi

echo ""
if [ $failed -eq 0 ]; then
  echo "✓ All services are healthy\!"
  exit 0
else
  echo "✗ $failed service(s) failed health check"
  exit 1
fi
