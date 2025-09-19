#!/bin/bash

# Script để dừng và cleanup containers

echo "🛑 Stopping Apartment Search App containers..."

# Stop containers
docker stop apartment-backend apartment-frontend 2>/dev/null || true

# Remove containers
docker rm apartment-backend apartment-frontend 2>/dev/null || true

# Remove network
docker network rm apartment-network 2>/dev/null || true

echo "✅ All containers stopped and cleaned up!"
echo ""
echo "🗂️ To remove Docker image as well:"
echo "   docker rmi apartment-app"