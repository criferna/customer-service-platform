"""
=============================================================================
PUNTO DE ENTRADA - Notifications Service (FastAPI)
=============================================================================
Servicio de notificaciones. Principalmente un EVENT CONSUMER.

Tiene una API REST mínima para consultar notificaciones generadas,
pero su trabajo principal ocurre en el consumer de RabbitMQ que
corre como tarea en background al iniciar el servicio.

PATRÓN: Event Consumer
  Al iniciar, se conecta a RabbitMQ y comienza a escuchar eventos.
  Cada evento genera una notificación automáticamente.
=============================================================================
"""

import asyncio
import logging
import os
import time

from fastapi import FastAPI, Depends, Query, Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_session
from src.infrastructure.database.models import NotificationModel
from src.infrastructure.messaging.event_consumer import start_consuming

SERVICE_NAME = os.getenv("SERVICE_NAME", "notifications-service")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=f'{{"timestamp":"%(asctime)s","service":"{SERVICE_NAME}","level":"%(levelname)s","message":"%(message)s"}}',
)
logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"])

app = FastAPI(
    title="Notifications Service",
    description="Microservicio de Notificaciones - Consume eventos y genera notificaciones automáticas.",
    version="1.0.0",
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    if request.url.path not in ("/health", "/metrics"):
        REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
        REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(duration)
    return response


@app.get("/health", tags=["Infrastructure"])
async def health():
    return {"status": "healthy", "service": SERVICE_NAME}


@app.get("/metrics", tags=["Infrastructure"])
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/notifications", tags=["Notifications"], summary="Listar notificaciones generadas")
async def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    recipient_id: str = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Lista las notificaciones generadas por eventos del sistema."""
    query = select(NotificationModel).order_by(NotificationModel.created_at.desc())
    if recipient_id:
        query = query.where(NotificationModel.recipient_id == recipient_id)
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    notifications = result.scalars().all()
    return [
        {
            "id": str(n.id),
            "event_type": n.event_type,
            "recipient_type": n.recipient_type,
            "recipient_email": n.recipient_email,
            "channel": n.channel,
            "subject": n.subject,
            "body": n.body,
            "status": n.status,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]


@app.on_event("startup")
async def startup():
    logger.info(f"{SERVICE_NAME} starting up...")
    # Iniciar consumer de eventos como tarea en background
    asyncio.create_task(start_consuming())
    logger.info(f"{SERVICE_NAME} ready - consuming events from RabbitMQ")


@app.on_event("shutdown")
async def shutdown():
    logger.info(f"{SERVICE_NAME} shutting down...")
