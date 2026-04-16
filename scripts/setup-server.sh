#!/usr/bin/env bash
# =============================================================================
# Setup Inicial del Servidor - Customer Service Platform
# =============================================================================
# Ejecutar UNA VEZ en el servidor para preparar el ambiente.
#
# Uso:
#   chmod +x scripts/setup-server.sh
#   ./scripts/setup-server.sh
#
# Acciones:
#   1. Clonar el repositorio
#   2. Crear archivos .env
#   3. Levantar Jenkins
#   4. Construir y desplegar todos los servicios
# =============================================================================

set -euo pipefail

REPO_URL="https://github.com/criferna/customer-service-platform.git"
APP_DIR="$HOME/apps/customer-service-platform"

echo "============================================"
echo "  Customer Service Platform - Server Setup"
echo "============================================"
echo ""

# 1. Clonar repositorio si no existe
if [ -d "$APP_DIR" ]; then
    echo "[INFO] Repository already exists, pulling latest..."
    cd "$APP_DIR" && git pull
else
    echo "[INFO] Cloning repository..."
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

# 2. Crear .env para infraestructura
if [ ! -f infrastructure/.env ]; then
    echo "[INFO] Creating infrastructure/.env..."
    cp infrastructure/.env.example infrastructure/.env
fi

# 3. Levantar Jenkins
echo "[INFO] Starting Jenkins..."
cd infrastructure
docker compose -f docker-compose.jenkins.yml up -d
echo "[INFO] Jenkins will be available at http://$(hostname -I | awk '{print $1}'):9080"
echo "[INFO] Initial password: docker exec cs-jenkins cat /var/jenkins_home/secrets/initialAdminPassword"

# 4. Construir y desplegar microservicios
echo "[INFO] Building and deploying all services..."
docker compose build
docker compose up -d

# 5. Esperar y verificar
echo "[INFO] Waiting 45s for services to start..."
sleep 45
cd ..
chmod +x scripts/health-check.sh
./scripts/health-check.sh

echo ""
echo "============================================"
echo "  Setup Complete!"
echo "============================================"
echo ""
echo "  API Gateway:    http://$(hostname -I | awk '{print $1}'):8000"
echo "  RabbitMQ UI:    http://$(hostname -I | awk '{print $1}'):15672"
echo "  Jenkins:        http://$(hostname -I | awk '{print $1}'):9080"
echo ""
