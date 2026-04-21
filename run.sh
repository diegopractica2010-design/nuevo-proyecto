#!/bin/bash

# Script de inicio para Radar de Precios

set -e

echo "🚀 Iniciando Radar de Precios..."

# Verificar si estamos en el directorio correcto
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Ejecuta este script desde el directorio raíz del proyecto"
    exit 1
fi

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo "📦 Activando entorno virtual..."
    source venv/bin/activate
else
    echo "⚠️  No se encontró entorno virtual. Instala dependencias manualmente."
fi

# Configurar PYTHONPATH
export PYTHONPATH=$(pwd)

# Verificar dependencias
echo "🔍 Verificando dependencias..."
python -c "import fastapi, uvicorn, requests, bs4" || {
    echo "❌ Faltan dependencias. Ejecuta: pip install -e ."
    exit 1
}

# Ejecutar tests si se solicita
if [ "$1" = "--test" ]; then
    echo "🧪 Ejecutando tests..."
    python -m pytest tests/ -v
    echo "✅ Tests completados"
fi

# Iniciar servidor
echo "🌐 Iniciando servidor en http://localhost:8001"
echo "Presiona Ctrl+C para detener"
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001