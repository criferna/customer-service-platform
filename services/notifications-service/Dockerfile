# =============================================================================
# Dockerfile - Notifications Service (Python / FastAPI)
# =============================================================================
# Servicio que CONSUME eventos del Event Bus y genera notificaciones.
# Demuestra el patrón Event Consumer en la arquitectura event-driven.
# =============================================================================

FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
LABEL service="notifications-service" team="customer-platform" pattern="microservice"
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY src/ ./src/
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "src.presentation.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
