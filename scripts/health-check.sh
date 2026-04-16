#!/usr/bin/env bash
# =============================================================================
# Health Check Script - Customer Service Platform
# =============================================================================
# Verifica el estado de salud de todos los componentes.
#
# Uso:
#   ./scripts/health-check.sh
#
# Verifica:
#   - Cada microservicio (/health endpoint)
#   - API Gateway (Kong)
#   - Event Bus (RabbitMQ)
#   - Bases de datos (PostgreSQL containers)
#
# PATRÓN: Observabilidad (Slide 20)
#   Monitoreo activo del estado de cada componente.
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

check_http() {
    local name="$1"
    local url="$2"
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
    if [ "$status" = "200" ]; then
        echo -e "  ${GREEN}✅${NC} ${name}: healthy (HTTP ${status})"
    else
        echo -e "  ${RED}❌${NC} ${name}: unhealthy (HTTP ${status})"
        ERRORS=$((ERRORS + 1))
    fi
}

check_container() {
    local name="$1"
    local container="$2"
    local health
    health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "not found")
    if [ "$health" = "healthy" ]; then
        echo -e "  ${GREEN}✅${NC} ${name}: ${health}"
    elif [ "$health" = "starting" ]; then
        echo -e "  ${YELLOW}⏳${NC} ${name}: ${health}"
    else
        echo -e "  ${RED}❌${NC} ${name}: ${health}"
        ERRORS=$((ERRORS + 1))
    fi
}

echo ""
echo "=========================================="
echo "  Customer Service Platform - Health Check"
echo "=========================================="
echo ""

echo "🗄️  Databases (PostgreSQL containers):"
for db in cs-customers-db cs-tickets-db cs-knowledge-db cs-notifications-db cs-agents-db; do
    check_container "$db" "$db"
done

echo ""
echo "📨 Event Bus:"
check_container "RabbitMQ" "cs-rabbitmq"

echo ""
echo "🌐 API Gateway:"
check_container "Kong" "cs-kong"

echo ""
echo "🔧 Microservices (via API Gateway http://localhost:8000):"
check_http "Customers Service"     "http://localhost:8000/api/v1/customers"
check_http "Tickets Service"       "http://localhost:8000/api/v1/tickets"
check_http "Articles Service"      "http://localhost:8000/api/v1/articles"
check_http "Notifications Service" "http://localhost:8000/api/v1/notifications"
check_http "Agents Service"        "http://localhost:8000/api/v1/agents"

echo ""
if [ "$ERRORS" -gt 0 ]; then
    echo -e "${RED}⚠️  ${ERRORS} component(s) unhealthy${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All components healthy!${NC}"
fi
echo ""
