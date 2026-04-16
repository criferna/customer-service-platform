# =============================================================================
# Dockerfile - Customers Service (Python / FastAPI)
# =============================================================================
# Multi-stage build para optimizar el tamaño de la imagen:
#   Stage 1 (builder): instala dependencias en un virtualenv
#   Stage 2 (runtime): copia solo lo necesario para ejecutar
#
# Esto demuestra buenas prácticas de contenedores (Slide 36-38):
#   - Imagen mínima (slim) reduce superficie de ataque
#   - Multi-stage reduce tamaño final (~100MB vs ~400MB)
#   - Non-root user por seguridad
#   - HEALTHCHECK integrado para auto-recovery
# =============================================================================

# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

WORKDIR /build

# Instalar dependencias primero (aprovecha cache de Docker layers)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.12-slim

# Metadatos del contenedor
LABEL service="customers-service" \
      team="customer-platform" \
      pattern="microservice"

# Crear usuario non-root (seguridad: no ejecutar como root)
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copiar dependencias instaladas desde el builder
COPY --from=builder /install /usr/local

# Copiar código fuente
COPY src/ ./src/

# Cambiar a usuario non-root
USER appuser

# Puerto interno del servicio
EXPOSE 8000

# Health check integrado en Docker para auto-recovery.
# Si este check falla 3 veces consecutivas, Docker reinicia el contenedor.
HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Ejecutar con uvicorn (ASGI server para FastAPI)
CMD ["uvicorn", "src.presentation.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
