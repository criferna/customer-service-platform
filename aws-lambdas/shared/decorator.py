# =============================================================================
# PATRON: DECORATOR (Estructural)
# =============================================================================
# QUÉ ES:
#   Añade responsabilidades a un objeto de forma dinámica, sin modificar
#   su clase original. Es una alternativa flexible a la herencia.
#   Los decoradores se "apilan" como capas alrededor del objeto base.
#
# POR QUÉ SE USA AQUÍ:
#   Los handlers de Lambda necesitan funcionalidad transversal (cross-cutting):
#     - Logging estructurado de cada invocación
#     - Propagación de Correlation ID para tracing distribuido
#     - Manejo centralizado de errores y respuestas HTTP
#     - Validación de input
#
#   Sin el patrón Decorator, tendríamos que repetir este código en cada
#   handler. Con decoradores, cada capa envuelve al handler base:
#
#     handler_final = with_logging(with_correlation_id(with_error_handler(handler_base)))
#
#   Cada decorador agrega su funcionalidad sin tocar el handler original.
#
# CUÁNDO USARLO EN PRODUCCIÓN:
#   - Middleware en APIs (auth, logging, caching, rate limiting)
#   - Retry con backoff exponencial
#   - Circuit breaker wrapper
#   - Caching transparente
#   - Transformación de request/response
#
# CUÁNDO NO USARLO:
#   - Si solo necesitas una capa simple (un if basta)
#   - Si el orden de los decoradores causa confusión
#   - Si hay demasiados decoradores apilados (más de 4-5)
# =============================================================================

import json
import logging
import time
import traceback
import uuid
from functools import wraps

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def with_error_handler(handler):
    """
    DECORATOR 1: Manejo centralizado de errores.

    Envuelve el handler para capturar excepciones y convertirlas
    en respuestas HTTP apropiadas. Sin esto, una excepción no
    capturada retornaría un 502 genérico de API Gateway.

    Jerarquía de errores:
      - ValueError → 400 Bad Request
      - KeyError   → 404 Not Found
      - Exception  → 500 Internal Server Error
    """

    @wraps(handler)
    def wrapper(event, context):
        try:
            return handler(event, context)
        except ValueError as e:
            logger.warning(f"Bad request: {e}")
            return _response(400, {"error": str(e)})
        except KeyError as e:
            logger.warning(f"Not found: {e}")
            return _response(404, {"error": f"Resource not found: {e}"})
        except Exception as e:
            logger.error(f"Internal error: {e}\n{traceback.format_exc()}")
            return _response(500, {"error": "Internal server error"})

    return wrapper


def with_correlation_id(handler):
    """
    DECORATOR 2: Propagación de Correlation ID.

    Implementa tracing distribuido:
      1. Si el request trae X-Correlation-ID en headers, lo reutiliza
      2. Si no trae, genera uno nuevo (UUID)
      3. Lo inyecta en el event para que el handler lo use
      4. Lo incluye en la respuesta HTTP

    Esto permite rastrear un request a través de múltiples servicios.
    En la versión Docker, Kong hacía esto. Aquí lo hace el decorator.
    """

    @wraps(handler)
    def wrapper(event, context):
        headers = event.get("headers") or {}
        # Buscar en headers (case-insensitive)
        correlation_id = None
        for key, value in headers.items():
            if key.lower() == "x-correlation-id":
                correlation_id = value
                break

        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Inyectar en el event para que el handler lo use
        event["correlation_id"] = correlation_id

        # Ejecutar handler
        response = handler(event, context)

        # Agregar correlation_id a los headers de respuesta
        if isinstance(response, dict) and "headers" in response:
            response["headers"]["X-Correlation-ID"] = correlation_id
        elif isinstance(response, dict):
            response["headers"] = {"X-Correlation-ID": correlation_id}

        return response

    return wrapper


def with_logging(handler):
    """
    DECORATOR 3: Logging estructurado de cada invocación.

    Registra:
      - Inicio: método HTTP, path, correlation_id
      - Fin: status code, duración en ms
      - Todo en formato JSON estructurado (facilita búsqueda en CloudWatch)

    Sin este decorator, cada handler tendría que implementar su propio logging.
    """

    @wraps(handler)
    def wrapper(event, context):
        start_time = time.time()

        method = event.get("httpMethod", "UNKNOWN")
        path = event.get("path", "UNKNOWN")
        correlation_id = event.get("correlation_id", "")
        service = event.get("service_name", context.function_name if context else "unknown")

        logger.info(json.dumps({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "service": service,
            "level": "INFO",
            "message": f"Incoming {method} {path}",
            "correlation_id": correlation_id,
            "method": method,
            "path": path,
        }))

        response = handler(event, context)

        duration_ms = (time.time() - start_time) * 1000
        status = response.get("statusCode", 0) if isinstance(response, dict) else 0

        logger.info(json.dumps({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "service": service,
            "level": "INFO",
            "message": f"Completed {method} {path} {status} {duration_ms:.1f}ms",
            "correlation_id": correlation_id,
            "status": status,
            "duration_ms": round(duration_ms, 1),
        }))

        return response

    return wrapper


def with_json_body(handler):
    """
    DECORATOR 4: Parseo automático del body JSON.

    Si el request tiene body, lo parsea de JSON a dict y lo inyecta
    en event["parsed_body"]. Si el JSON es inválido, retorna 400.
    """

    @wraps(handler)
    def wrapper(event, context):
        body = event.get("body")
        if body:
            try:
                event["parsed_body"] = json.loads(body)
            except json.JSONDecodeError:
                return _response(400, {"error": "Invalid JSON in request body"})
        else:
            event["parsed_body"] = {}
        return handler(event, context)

    return wrapper


def lambda_handler(*decorators):
    """
    Función de conveniencia que aplica todos los decoradores estándar
    más cualquier decorador adicional.

    Uso:
        @lambda_handler()
        def handler(event, context):
            ...

        # Equivale a:
        # handler = with_logging(with_correlation_id(with_error_handler(with_json_body(handler))))

    Los decoradores se aplican de adentro hacia afuera:
        1. with_json_body  (más interno - parsea body primero)
        2. with_error_handler (captura errores)
        3. with_correlation_id (inyecta tracing)
        4. with_logging (más externo - loguea todo)
    """

    def decorator(handler):
        wrapped = with_json_body(handler)
        wrapped = with_error_handler(wrapped)
        for dec in reversed(decorators):
            wrapped = dec(wrapped)
        wrapped = with_correlation_id(wrapped)
        wrapped = with_logging(wrapped)
        return wrapped

    return decorator


# ---------------------------------------------------------------------------
# Helper para respuestas HTTP
# ---------------------------------------------------------------------------
def _response(status_code: int, body: dict) -> dict:
    """Construye una respuesta compatible con API Gateway proxy integration."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,X-Correlation-ID",
        },
        "body": json.dumps(body, default=str),
    }


def response(status_code: int, body) -> dict:
    """Versión pública del helper de respuesta."""
    return _response(status_code, body)
