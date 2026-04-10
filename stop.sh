#\!/bin/bash

set -e

echo "Stopping Synora services..."
docker-compose down

echo "✓ All services stopped"
