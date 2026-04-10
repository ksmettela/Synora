#!/bin/bash

# Load test script for fingerprint-ingestor
# Usage: ./load-test.sh [num_requests] [batch_size] [concurrency]

NUM_REQUESTS=${1:-1000}
BATCH_SIZE=${2:-10}
CONCURRENCY=${3:-10}
BASE_URL=${BASE_URL:-http://localhost:8080}
API_KEY=${API_KEY:-test-key}

echo "Load Testing Fingerprint Ingestor"
echo "=================================="
echo "Base URL: $BASE_URL"
echo "Requests: $NUM_REQUESTS"
echo "Batch Size: $BATCH_SIZE"
echo "Concurrency: $CONCURRENCY"
echo ""

# Check if server is running
if ! curl -s "$BASE_URL/health" > /dev/null; then
    echo "Error: Server not accessible at $BASE_URL"
    exit 1
fi

# Create temporary request file
TEMP_DIR=$(mktemp -d)
REQUEST_FILE="$TEMP_DIR/request.json"

# Generate request body
generate_request() {
    local batch_size=$1
    echo "{"
    echo '  "batch": ['

    for ((i=0; i<batch_size; i++)); do
        if [ $i -gt 0 ]; then echo ","; fi

        # Generate random hex strings
        local device_id=$(openssl rand -hex 32)
        local fingerprint_hash=$(openssl rand -hex 32)
        local timestamp=$(date +%s)000

        cat <<EOF
    {
      "device_id": "$device_id",
      "fingerprint_hash": "$fingerprint_hash",
      "timestamp_utc": $timestamp,
      "manufacturer": "LG",
      "model": "OLED55C3",
      "ip_address": "192.168.1.$((RANDOM % 255 + 1))"
    }
EOF
    done

    echo ""
    echo "  ]"
    echo "}"
}

# Generate request
generate_request "$BATCH_SIZE" > "$REQUEST_FILE"

echo "Running load test..."
echo ""

# Run requests with ab (Apache Bench) if available, otherwise use seq + curl
if command -v ab &> /dev/null; then
    # Use Apache Bench for better load testing
    ab -n "$NUM_REQUESTS" \
       -c "$CONCURRENCY" \
       -p "$REQUEST_FILE" \
       -H "X-API-Key: $API_KEY" \
       -H "Content-Type: application/json" \
       "$BASE_URL/v1/fingerprints"
else
    # Fallback: use curl with GNU Parallel if available
    if command -v parallel &> /dev/null; then
        seq 1 "$NUM_REQUESTS" | parallel -j "$CONCURRENCY" \
            "curl -s -X POST $BASE_URL/v1/fingerprints \
                   -H 'X-API-Key: $API_KEY' \
                   -H 'Content-Type: application/json' \
                   -d @$REQUEST_FILE > /dev/null && echo -n '.'"
        echo ""
    else
        # Simple sequential fallback
        echo "Note: Install 'apache2-utils' for better load testing: ab -n 1000 -c 10"
        echo ""

        for ((i=1; i<=NUM_REQUESTS; i++)); do
            if (( i % CONCURRENCY == 0 )); then
                for ((j=0; j<CONCURRENCY; j++)); do
                    curl -s -X POST "$BASE_URL/v1/fingerprints" \
                        -H "X-API-Key: $API_KEY" \
                        -H "Content-Type: application/json" \
                        -d @"$REQUEST_FILE" > /dev/null &
                done
                wait
                echo "Sent $i requests..."
            fi
        done
    fi
fi

echo ""
echo "Load test complete!"
echo ""

# Show health status
echo "Server health:"
curl -s "$BASE_URL/health" | jq .

# Show sample metrics
echo ""
echo "Sample metrics (last 5 lines):"
curl -s "http://localhost:9090/metrics" | grep acraas | tail -5

# Cleanup
rm -rf "$TEMP_DIR"
