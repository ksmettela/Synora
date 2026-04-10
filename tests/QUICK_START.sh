#\!/bin/bash
# Quick start script for ACRaaS test suite

set -e

echo "================================"
echo "ACRaaS Test Suite Quick Start"
echo "================================"
echo ""

# Check Python version
echo "[1/5] Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version found"
echo ""

# Install dependencies
echo "[2/5] Installing test dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Verify services
echo "[3/5] Checking service availability..."
services=(
    "http://localhost:8080/health"
    "http://localhost:8082/health"
    "http://localhost:8084/health"
    "http://localhost:8085/health"
)

for service in "${services[@]}"; do
    if curl -s "$service" > /dev/null 2>&1; then
        echo "✓ $service is healthy"
    else
        echo "⚠ Warning: $service is unreachable"
    fi
done
echo ""

# Run fast tests
echo "[4/5] Running fast integration tests..."
echo "(Excluding slow end-to-end tests)"
pytest integration/ -m "not slow" -v --tb=short 2>&1 | tail -20
echo ""

# Show next steps
echo "[5/5] Test suite ready\!"
echo ""
echo "Common commands:"
echo "  pytest integration/ -m \"not slow\" -v"
echo "  pytest integration/ -v"
echo "  pytest integration/test_ingestor.py -v"
echo "  locust -f load/locustfile.py --headless -u 100 -r 10 --run-time 60s"
echo ""
echo "For more info, see README.md"
