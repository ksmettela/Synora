#\!/bin/bash

set -e

echo "Stopping ACRaaS services..."
docker-compose down

echo "✓ All services stopped"
