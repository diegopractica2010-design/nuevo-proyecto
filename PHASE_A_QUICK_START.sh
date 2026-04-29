#!/bin/bash
# PHASE_A_QUICK_START.sh - Inicio rápido Fase A en Docker

set -e

echo "=========================================="
echo "RADAR DE PRECIOS - FASE A (QUICK START)"
echo "=========================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no instalado. Instala desde: https://www.docker.com"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose no instalado."
    exit 1
fi

echo "✅ Docker encontrado"
echo ""

# Check .env
if [ ! -f .env ]; then
    echo "⚠️  Creando .env desde .env.example..."
    cp .env.example .env
    echo "✅ .env creado (revisa y actualiza si es necesario)"
else
    echo "✅ .env ya existe"
fi

echo ""
echo "Iniciando servicios..."
echo ""

# Build (si no existe)
if [ -z "$(docker images -q radar-precios-app)" ]; then
    echo "🔨 Building images..."
    docker-compose build
fi

# Up services
echo "🚀 Starting containers..."
docker-compose up -d

echo ""
echo "✅ Servicios iniciados:"
echo "  - App: http://localhost:8001"
echo "  - Health: http://localhost:8001/health"
echo "  - Search: http://localhost:8001/search?q=leche&store=lider"
echo "  - Docs: http://localhost:8001/docs"
echo ""

# Wait for app to be ready
echo "⏳ Esperando app startup (max 30s)..."
for i in {1..30}; do
    if curl -s http://localhost:8001/health > /dev/null; then
        echo "✅ App ready!"
        break
    fi
    echo -n "."
    sleep 1
done

echo ""
echo "=========================================="
echo "PRÓXIMOS PASOS:"
echo "=========================================="
echo ""
echo "1. Ver logs:"
echo "   docker-compose logs -f app"
echo ""
echo "2. Test de búsqueda:"
echo "   curl 'http://localhost:8001/search?q=leche&store=lider'"
echo ""
echo "3. Test de rate limiting (>10 requests/min):"
echo "   for i in {1..15}; do curl http://localhost:8001/health; done"
echo ""
echo "4. Ver celery workers:"
echo "   docker-compose logs -f celery_worker"
echo ""
echo "5. Conectar a Redis:"
echo "   docker exec -it radar-redis redis-cli -a redis123"
echo ""
echo "6. Detener servicios:"
echo "   docker-compose down"
echo ""
echo "=========================================="
