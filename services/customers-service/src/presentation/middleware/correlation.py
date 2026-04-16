"""
=============================================================================
MIDDLEWARE - Correlation ID (Tracing Distribuido)
=============================================================================
Implementa el patrón de Correlation ID para observabilidad (Slide 20).

Cada request que entra al sistema recibe un ID único (X-Correlation-ID).
Si el API Gateway (Kong) ya inyectó uno, se reutiliza.
Este ID se propaga:
  1. En los logs del servicio
  2. En los eventos publicados a RabbitMQ
  3. En las respuestas HTTP al cliente
  4. En las llamadas a otros servicios (si las hubiera)

Esto permite rastrear una operación completa a través de múltiples
servicios en los logs centralizados.

Ejemplo de traza:
  [correlation_id=abc-123] Kong recibe GET /api/v1/tickets/1
  [correlation_id=abc-123] tickets-service procesa el request
  [correlation_id=abc-123] tickets-service consulta customers-service
  [correlation_id=abc-123] tickets-service responde al cliente
=============================================================================
"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# ContextVar permite almacenar el correlation_id de forma thread/async-safe.
# Cada request concurrente tiene su propio valor.
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware que extrae o genera un Correlation ID para cada request.
    Lo almacena en un ContextVar para que esté disponible en toda la cadena.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Si Kong (API Gateway) ya inyectó un X-Correlation-ID, lo usamos.
        # Si no (request directo), generamos uno nuevo.
        corr_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        # Almacenar en ContextVar (disponible en toda la cadena async)
        correlation_id_var.set(corr_id)

        # Continuar con el request
        response = await call_next(request)

        # Incluir el correlation ID en la respuesta (para debugging del cliente)
        response.headers["X-Correlation-ID"] = corr_id

        return response


def get_correlation_id() -> str:
    """Obtiene el correlation ID del request actual."""
    return correlation_id_var.get("")
