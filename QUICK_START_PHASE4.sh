#!/bin/bash
# ============================================================================
# RADAR DE PRECIOS - FASE 4: QUICK START (PRODUCCIÓN & OPERACIÓN)
# ============================================================================
# Script para iniciar la aplicación completa con Docker Compose
# Incluye: API, DB, Redis, Celery, Prometheus, Grafana, Alertmanager

set -e

echo "🚀 Radar de Precios - Fase 4 Quick Start"
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose."
    exit 1
fi

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration before continuing"
    nano .env || echo "Skipped editing .env"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/logs
mkdir -p data/backups
mkdir -p data/backups_s3 2>/dev/null || true

# Build images
echo "🔨 Building Docker images..."
docker-compose build

# Start basic stack (API + DB + Redis)
echo "🎯 Starting basic stack (API, PostgreSQL, Redis)..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
echo "🏥 Checking health..."
curl -s http://localhost:8001/health || echo "API not ready yet..."

# Run migrations
echo "🗄️  Running database migrations..."
docker-compose exec -T app alembic upgrade head || true

# Start monitoring stack
echo "📊 Starting monitoring stack (Prometheus, Grafana, Alertmanager)..."
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d || echo "Monitoring stack failed, but API is running"

echo ""
echo "✅ Radar de Precios is running!"
echo ""
echo "🌐 Access points:"
echo "  API:           http://localhost:8001"
echo "  Frontend:      http://localhost:8001/"
echo "  Health Check:  http://localhost:8001/health"
echo "  Metrics:       http://localhost:8001/metrics"
echo ""
echo "📊 Monitoring (if stack started):"
echo "  Grafana:       http://localhost:3000 (admin/admin)"
echo "  Prometheus:    http://localhost:9090"
echo "  Alertmanager:  http://localhost:9093"
echo "  Flower (Celery): http://localhost:5555"
echo ""
echo "📚 Documentation:"
echo "  Deployment:    See DEPLOYMENT.md"
echo "  API Docs:      http://localhost:8001/docs"
echo ""
echo "🔧 Useful commands:"
echo "  View logs:     docker-compose logs -f app"
echo "  Celery logs:   docker-compose logs -f celery_worker"
echo "  Run tests:     docker-compose exec app pytest tests/ -v"
echo "  Database shell: docker-compose exec app psql -U radar -d radar_precios"
echo "  Redis CLI:     docker-compose exec redis redis-cli"
echo ""
echo "🛑 Stop services:  docker-compose down"
echo "🔄 Restart:        docker-compose restart"
echo ""
