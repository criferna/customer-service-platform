"""
=============================================================================
PUNTO DE ENTRADA - Customers Service (FastAPI Application)
=============================================================================
Configura y arranca el microservicio de Clientes.

Este archivo orquesta:
  1. Configuración de logging estructurado (JSON) para observabilidad
  2. Middleware de Correlation ID para tracing distribuido
  3. Endpoints de salud (/health) y métricas (/metrics)
  4. Rutas de la API de clientes
  5. Lifecycle hooks (startup/shutdown) para conexiones

OBSERVABILIDAD (Slide 20):
  - /health: Health check para Docker y Kong (auto-recovery)
  - /metrics: Métricas Prometheus (requests, latencia, errores)
  - Logs JSON con correlation_id (tracing entre servicios)

RESILIENCIA (Slide 19):
  - Health checks permiten que Docker reinicie el contenedor si falla
  - Kong detecta servicios unhealthy y deja de enviarles tráfico
=============================================================================
"""

import logging
import os
import time

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from src.presentation.middleware.correlation import CorrelationIdMiddleware
from src.presentation.routes.customer_routes import router as customer_router, _event_publisher

# =============================================================================
# Logging Estructurado (JSON)
# =============================================================================
# Logs en formato JSON para que herramientas como Grafana/Loki puedan
# parsearlos y crear dashboards automáticamente.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SERVICE_NAME = os.getenv("SERVICE_NAME", "customers-service")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=f'{{"timestamp":"%(asctime)s","service":"{SERVICE_NAME}","level":"%(levelname)s","message":"%(message)s"}}',
)
logger = logging.getLogger(__name__)

# =============================================================================
# Métricas Prometheus
# =============================================================================
# Estas métricas se exponen en /metrics y son scrapeadas por Prometheus.
# Se visualizan en el dashboard de Grafana existente.
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)

# =============================================================================
# Aplicación FastAPI
# =============================================================================
app = FastAPI(
    title="Customers Service",
    description=(
        "Microservicio de Gestión de Clientes - Bounded Context: Customers.\n\n"
        "**Patrones implementados:**\n"
        "- DDD (Domain-Driven Design) con capas: Domain, Application, Infrastructure, Presentation\n"
        "- Event-Driven Architecture: publica eventos a RabbitMQ\n"
        "- Database per Service: BD PostgreSQL exclusiva\n"
        "- API Gateway: accesible via Kong en http://192.168.0.125:8000/api/v1/customers"
    ),
    version="1.0.0",
)

# Middleware para Correlation ID (tracing distribuido)
app.add_middleware(CorrelationIdMiddleware)


# Middleware para métricas Prometheus
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Registra métricas de cada request para Prometheus."""
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    # No registrar métricas de los endpoints de salud/métricas
    if request.url.path not in ("/health", "/metrics"):
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)

    return response


# Incluir rutas de la API de clientes
app.include_router(customer_router)


# =============================================================================
# Health Check Endpoint
# =============================================================================
@app.get(
    "/health",
    tags=["Infrastructure"],
    summary="Health check del servicio",
    description="Usado por Docker HEALTHCHECK y Kong para auto-recovery.",
)
async def health():
    """
    Health check endpoint.
    Docker lo usa para determinar si el contenedor está sano.
    Kong lo usa para saber si debe enviar tráfico a esta instancia.
    Si falla, Docker reinicia el contenedor (auto-recovery).
    """
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
    }


# =============================================================================
# Métricas Prometheus Endpoint
# =============================================================================
@app.get(
    "/metrics",
    tags=["Infrastructure"],
    summary="Métricas Prometheus",
    description="Endpoint scrapeado por Prometheus para monitoreo.",
)
async def metrics():
    """Expone métricas en formato Prometheus."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# =============================================================================
# Lifecycle Hooks
# =============================================================================
@app.on_event("startup")
async def startup():
    """Conectar al Event Bus al iniciar el servicio."""
    logger.info(f"{SERVICE_NAME} starting up...")
    await _event_publisher.connect()
    logger.info(f"{SERVICE_NAME} ready")


@app.on_event("shutdown")
async def shutdown():
    """Desconectar del Event Bus al apagar el servicio."""
    logger.info(f"{SERVICE_NAME} shutting down...")
    await _event_publisher.disconnect()
