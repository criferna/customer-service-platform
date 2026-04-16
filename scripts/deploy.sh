#!/usr/bin/env bash
# =============================================================================
# Script de Despliegue - Customer Service Platform
# =============================================================================
# Despliega o actualiza todos los microservicios en el servidor.
#
# Uso:
#   ./scripts/deploy.sh              # Deploy completo
#   ./scripts/deploy.sh --build      # Reconstruir imágenes y deploy
#   ./scripts/deploy.sh --service customers-service  # Deploy solo un servicio
#
# Este script es usado por Jenkins y también puede ejecutarse manualmente.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INFRA_DIR="${PROJECT_DIR}/infrastructure"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parsear argumentos
BUILD=false
SERVICE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --build)   BUILD=true; shift ;;
        --service) SERVICE="$2"; shift 2 ;;
        *)         log_error "Unknown option: $1"; exit 1 ;;
    esac
done

cd "$INFRA_DIR"

# Crear .env si no existe
if [ ! -f .env ]; then
    log_info "Creating .env from .env.example..."
    cp .env.example .env
fi

# Construir imágenes si se pidió
if [ "$BUILD" = true ]; then
    if [ -n "$SERVICE" ]; then
        log_info "Building ${SERVICE}..."
        docker compose build "$SERVICE"
    else
        log_info "Building all services..."
        docker compose build
    fi
fi

# Desplegar
if [ -n "$SERVICE" ]; then
    log_info "Deploying ${SERVICE}..."
    docker compose up -d --force-recreate "$SERVICE"
else
    log_info "Deploying all services..."
    docker compose up -d --force-recreate --remove-orphans
fi

# Esperar a que los servicios se estabilicen
log_info "Waiting for services to start..."
sleep 15

# Verificar health
"${SCRIPT_DIR}/health-check.sh"

log_info "Deploy completed!"
