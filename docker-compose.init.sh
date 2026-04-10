#!/bin/bash

set -e

KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}"
SCYLLA_HOST="${SCYLLA_HOST:-scylladb}"
SCYLLA_PORT="${SCYLLA_PORT:-9042}"
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-acraas}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-acraas_pass}"
POSTGRES_DB="${POSTGRES_DB:-acraas}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-minio:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-acraas_access}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-acraas_secret}"

echo "================================================"
echo "Synora Initialization Script"
echo "================================================"
echo ""

# Function to wait for service
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    local max_attempts=30
    local attempt=1

    echo "Waiting for $service to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if nc -z $host $port 2>/dev/null; then
            echo "✓ $service is ready"
            return 0
        fi
        echo "  Attempt $attempt/$max_attempts..."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo "✗ $service failed to start"
    return 1
}

# Wait for Kafka
echo ""
echo "--- Waiting for Kafka ---"
wait_for_service kafka 9092 "Kafka" || exit 1
sleep 3

# Create Kafka topics
echo ""
echo "--- Creating Kafka Topics ---"
KAFKA_CONTAINER="kafka"

create_topic() {
    local topic=$1
    echo "Creating topic: $topic"
    docker exec $KAFKA_CONTAINER kafka-topics.sh \
        --bootstrap-server localhost:9092 \
        --create \
        --topic $topic \
        --partitions 6 \
        --replication-factor 1 \
        --if-not-exists \
        --config retention.ms=604800000 \
        2>/dev/null || true
}

create_topic "raw.fingerprints"
create_topic "matched.viewership"
create_topic "unmatched.fingerprints"
create_topic "consent.events"
create_topic "segmentation.updates"
create_topic "billing.events"

echo "✓ Kafka topics created"

# Wait for ScyllaDB
echo ""
echo "--- Waiting for ScyllaDB ---"
wait_for_service $SCYLLA_HOST $SCYLLA_PORT "ScyllaDB" || exit 1
sleep 2

# Initialize ScyllaDB
echo ""
echo "--- Initializing ScyllaDB ---"

docker exec -i $KAFKA_CONTAINER sleep 1 || true

cqlsh_init() {
    local cql=$1
    docker exec -i acraas-scylladb cqlsh -e "$cql" 2>/dev/null || echo "Warning: CQL command may have failed"
}

cqlsh_init "CREATE KEYSPACE IF NOT EXISTS acraas WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};"

cqlsh_init "
CREATE TABLE IF NOT EXISTS acraas.fingerprints (
    fingerprint_id UUID PRIMARY KEY,
    device_id UUID,
    user_agent TEXT,
    ip_address TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    metadata MAP<TEXT, TEXT>
);"

cqlsh_init "
CREATE TABLE IF NOT EXISTS acraas.viewer_events (
    event_id UUID,
    viewer_id UUID,
    fingerprint_id UUID,
    campaign_id TEXT,
    timestamp TIMESTAMP,
    metadata MAP<TEXT, TEXT>,
    PRIMARY KEY ((viewer_id), timestamp, event_id)
) WITH CLUSTERING ORDER BY (timestamp DESC);"

cqlsh_init "
CREATE TABLE IF NOT EXISTS acraas.segments (
    segment_id UUID PRIMARY KEY,
    segment_name TEXT,
    description TEXT,
    audience_size INT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);"

echo "✓ ScyllaDB initialized"

# Wait for PostgreSQL
echo ""
echo "--- Waiting for PostgreSQL ---"
wait_for_service $POSTGRES_HOST $POSTGRES_PORT "PostgreSQL" || exit 1
sleep 2

# Initialize PostgreSQL
echo ""
echo "--- Initializing PostgreSQL ---"

# Check and create databases
docker exec -i acraas-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB <<EOF
-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Consent Database Schema
CREATE TABLE IF NOT EXISTS consents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    consent_type VARCHAR(50) NOT NULL,
    granted BOOLEAN NOT NULL DEFAULT false,
    granted_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_consents_user_id ON consents(user_id);
CREATE INDEX IF NOT EXISTS idx_consents_consent_type ON consents(consent_type);
CREATE INDEX IF NOT EXISTS idx_consents_expires_at ON consents(expires_at);

-- Audit Log Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    details JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- Billing Database Schema
CREATE TABLE IF NOT EXISTS advertisers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    stripe_customer_id VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_advertisers_email ON advertisers(email);
CREATE INDEX IF NOT EXISTS idx_advertisers_stripe_customer_id ON advertisers(stripe_customer_id);

CREATE TABLE IF NOT EXISTS billing_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    advertiser_id UUID NOT NULL REFERENCES advertisers(id),
    event_type VARCHAR(50) NOT NULL,
    amount_cents BIGINT NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (advertiser_id) REFERENCES advertisers(id)
);

CREATE INDEX IF NOT EXISTS idx_billing_events_advertiser_id ON billing_events(advertiser_id);
CREATE INDEX IF NOT EXISTS idx_billing_events_event_type ON billing_events(event_type);
CREATE INDEX IF NOT EXISTS idx_billing_events_created_at ON billing_events(created_at);

CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    advertiser_id UUID NOT NULL REFERENCES advertisers(id),
    billing_period_start DATE NOT NULL,
    billing_period_end DATE NOT NULL,
    total_amount_cents BIGINT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    stripe_invoice_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (advertiser_id) REFERENCES advertisers(id)
);

CREATE INDEX IF NOT EXISTS idx_invoices_advertiser_id ON invoices(advertiser_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at);

-- API Keys Table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    advertiser_id UUID NOT NULL REFERENCES advertisers(id),
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    FOREIGN KEY (advertiser_id) REFERENCES advertisers(id)
);

CREATE INDEX IF NOT EXISTS idx_api_keys_advertiser_id ON api_keys(advertiser_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
EOF

echo "✓ PostgreSQL initialized"

# Wait for MinIO
echo ""
echo "--- Waiting for MinIO ---"
wait_for_service minio 9000 "MinIO" || exit 1
sleep 2

# Initialize MinIO buckets
echo ""
echo "--- Creating MinIO Buckets ---"

create_bucket() {
    local bucket=$1
    echo "Creating bucket: $bucket"
    docker exec acraas-minio mc alias set acraas http://minio:9000 $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
    docker exec acraas-minio mc mb acraas/$bucket --ignore-existing 2>/dev/null || true
    docker exec acraas-minio mc version enable acraas/$bucket 2>/dev/null || true
}

create_bucket "acraas-viewership"
create_bucket "acraas-archives"
create_bucket "acraas-events"

echo "✓ MinIO buckets created"

# Summary
echo ""
echo "================================================"
echo "✓ Synora Initialization Complete!"
echo "================================================"
echo ""
echo "Service URLs:"
echo "  Kafka UI:           http://localhost:8080"
echo "  ScyllaDB:           localhost:9042"
echo "  PostgreSQL:         localhost:5432"
echo "  Redis:              localhost:6379"
echo "  MinIO Console:      http://localhost:9001 (access: acraas_access / acraas_secret)"
echo "  Trino:              http://localhost:8088"
echo "  Prometheus:         http://localhost:9090"
echo "  Grafana:            http://localhost:3001 (admin / admin)"
echo "  Jaeger:             http://localhost:16686"
echo "  Airflow:            http://localhost:8089"
echo ""
echo "API Services:"
echo "  Fingerprint Ingestor:  http://localhost:8080"
echo "  Matching Engine:       http://localhost:8081"
echo "  Fingerprint Indexer:   http://localhost:8082"
echo "  Segmentation Engine:   http://localhost:8083"
echo "  Advertiser API:        http://localhost:8084"
echo "  Privacy Service:       http://localhost:8085"
echo "  Billing Service:       http://localhost:8086"
echo ""
echo "Frontend:              http://localhost:3000"
echo ""
