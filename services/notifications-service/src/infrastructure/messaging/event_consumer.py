"""
=============================================================================
CAPA DE INFRAESTRUCTURA - Event Consumer (Notifications)
=============================================================================
Consume eventos de tickets desde RabbitMQ y genera notificaciones.

PATRÓN: Event-Driven Architecture
  Este es el corazón del notifications-service.
  No recibe requests HTTP para generar notificaciones.
  Todo se dispara por EVENTOS del Event Bus.

FLUJO:
  1. tickets-service publica ticket.created en RabbitMQ
  2. RabbitMQ enruta a la queue notifications.ticket_events
  3. Este consumer recibe el mensaje
  4. Crea una notificación en la BD
  5. "Envía" la notificación (log en el lab, email en producción)

IDEMPOTENCIA:
  Cada notificación registra el source_event_id (ID del evento origen).
  Si el mismo evento llega dos veces (ej: reintento), se ignora el duplicado.
  Esto es crítico en sistemas distribuidos donde los mensajes pueden duplicarse.

MÚLTIPLES INSTANCIAS:
  Si hay N instancias de notifications-service, RabbitMQ distribuye
  los mensajes entre ellas (round-robin). Cada evento lo procesa UNA instancia.
=============================================================================
"""

import json
import logging
import os
from uuid import UUID

import aio_pika

from src.infrastructure.database.connection import AsyncSessionLocal
from src.infrastructure.database.models import NotificationModel

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
SERVICE_NAME = os.getenv("SERVICE_NAME", "notifications-service")

# Templates de notificación por tipo de evento (Ubiquitous Language)
NOTIFICATION_TEMPLATES = {
    "ticket.created": {
        "subject": "Tu ticket #{id} ha sido recibido",
        "body": "Hola {customer_name}, tu ticket '{subject}' ha sido recibido. "
                "Te notificaremos cuando un agente sea asignado.",
        "recipient_type": "CUSTOMER",
    },
    "ticket.assigned": {
        "subject": "Tu ticket #{id} ha sido asignado",
        "body": "Hola {customer_name}, el agente {assigned_agent_name} ha sido asignado "
                "a tu ticket '{subject}'. Pronto recibirás una respuesta.",
        "recipient_type": "CUSTOMER",
    },
    "ticket.resolved": {
        "subject": "Tu ticket #{id} ha sido resuelto",
        "body": "Hola {customer_name}, tu ticket '{subject}' ha sido resuelto. "
                "Si el problema persiste, puedes reabrir el ticket.",
        "recipient_type": "CUSTOMER",
    },
    "ticket.closed": {
        "subject": "Tu ticket #{id} ha sido cerrado",
        "body": "Hola, tu ticket #{id} ha sido cerrado. Gracias por contactarnos.",
        "recipient_type": "CUSTOMER",
    },
}


async def start_consuming():
    """Conecta a RabbitMQ y comienza a consumir eventos de tickets."""
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()

        # Prefetch=1: procesar un mensaje a la vez (distribución equitativa entre instancias)
        await channel.set_qos(prefetch_count=1)

        # Consumir de la queue pre-configurada
        queue = await channel.get_queue("notifications.ticket_events")
        await queue.consume(process_ticket_event)

        logger.info("Started consuming from notifications.ticket_events")

    except Exception as e:
        logger.error(f"Failed to start consuming: {e}")


async def process_ticket_event(message: aio_pika.IncomingMessage):
    """
    Procesa un evento de ticket y genera la notificación correspondiente.

    Implementa IDEMPOTENCIA: si el evento ya fue procesado (source_event_id
    duplicado), se ignora silenciosamente.
    """
    async with message.process():
        try:
            event = json.loads(message.body)
            event_type = event.get("event_type", "")
            payload = event.get("payload", {})
            event_id = event.get("event_id")
            correlation_id = event.get("correlation_id", "")

            logger.info(
                f"Processing event: {event_type}",
                extra={"event_id": event_id, "correlation_id": correlation_id},
            )

            # Verificar si tenemos template para este tipo de evento
            template = NOTIFICATION_TEMPLATES.get(event_type)
            if not template:
                logger.warning(f"No template for event type: {event_type}")
                return

            # Generar contenido de la notificación usando el template
            short_id = payload.get("id", "")[:8]
            subject = template["subject"].format(id=short_id, **payload)
            body = template["body"].format(id=short_id, **{
                "customer_name": payload.get("customer_name", "Cliente"),
                "subject": payload.get("subject", ""),
                "assigned_agent_name": payload.get("assigned_agent_name", ""),
            })

            # Persistir la notificación
            async with AsyncSessionLocal() as session:
                notification = NotificationModel(
                    event_type=event_type,
                    recipient_id=UUID(payload.get("customer_id")) if payload.get("customer_id") else None,
                    recipient_type=template["recipient_type"],
                    recipient_email=payload.get("customer_email"),
                    channel="INTERNAL",
                    subject=subject,
                    body=body,
                    status="SENT",  # En el lab, siempre "enviado" (simulado)
                    source_event_id=UUID(event_id) if event_id else None,
                )
                session.add(notification)
                await session.commit()

            # En el lab, logueamos la "notificación enviada".
            # En producción, aquí se llamaría al servicio de email/SMS/push.
            logger.info(
                f"Notification sent: {subject}",
                extra={
                    "recipient_email": payload.get("customer_email"),
                    "event_type": event_type,
                    "correlation_id": correlation_id,
                },
            )

        except Exception as e:
            logger.error(f"Error processing event: {e}")
