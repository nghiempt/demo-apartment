#!/bin/bash

# Script để chạy containers với Docker commands thay vì docker-compose
# Workaround cho lỗi ContainerConfig trong docker-compose 1.29.2

echo "🐳 Starting Apartment Search App with Docker..."

# Load environment variables
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found. Please copy from .env.example and configure."
    exit 1
fi

# Read OPENAI_API_KEY from .env
export $(grep -v '^#' .env | xargs)

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY not found in .env file."
    exit 1
fi

# Stop and remove existing containers
echo "🛑 Stopping existing containers..."
docker stop apartment-backend apartment-frontend 2>/dev/null || true
docker rm apartment-backend apartment-frontend 2>/dev/null || true

# Build Docker image
echo "🔨 Building Docker image..."
docker build -t apartment-app .

# Create Docker network
echo "🌐 Creating Docker network..."
docker network create apartment-network 2>/dev/null || true

# Run Backend container
echo "🚀 Starting Backend (FastAPI)..."
docker run -d \
    --name apartment-backend \
    --network apartment-network \
    -p 8000:8000 \
    -e OPENAI_API_KEY="$OPENAI_API_KEY" \
    apartment-app \
    uvicorn main:app --host 0.0.0.0 --port 8000

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Run Frontend container
echo "🎨 Starting Frontend (Streamlit)..."
docker run -d \
    --name apartment-frontend \
    --network apartment-network \
    -p 8501:8501 \
    -e OPENAI_API_KEY="$OPENAI_API_KEY" \
    -e API_BASE_URL="http://apartment-backend:8000" \
    apartment-app \
    streamlit run chat_ui.py --server.port 8501 --server.address 0.0.0.0

echo ""
echo "✅ All containers started successfully!"
echo ""
echo "🔗 Access your application:"
echo "   🌐 Frontend (Streamlit): http://localhost:8501"
echo "   📡 Backend API: http://localhost:8000"
echo "   📋 API Documentation: http://localhost:8000/docs"
echo ""
echo "📊 Check container status:"
echo "   docker ps"
echo ""
echo "🛑 To stop all containers:"
echo "   ./stop-docker.sh"