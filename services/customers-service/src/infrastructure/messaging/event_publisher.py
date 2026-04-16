"""
=============================================================================
CAPA DE INFRAESTRUCTURA - Publicador de Eventos (Event Publisher)
=============================================================================
Publica eventos de dominio al Event Bus (RabbitMQ).

PATRÓN: Event-Driven Architecture
  Cuando algo ocurre en el dominio (ej: se crea un cliente),
  se publica un evento en el exchange 'domain.events' de RabbitMQ.

  La routing key (ej: 'customer.created') determina a qué queues
  llega el mensaje. Los bindings en RabbitMQ definen el enrutamiento:
    - customer.* → tickets.customer_events queue
    - customer.* → (otros servicios interesados)

PATRÓN: Resiliencia
  Si RabbitMQ no está disponible, el publisher loguea el error
  pero NO bloquea la operación principal. El evento se pierde
  (en producción usaríamos Transactional Outbox para evitar esto).

REFERENCIA: Slide 46 - Event Bus en la arquitectura tipo
=============================================================================
"""

import json
import logging
import os
from dataclasses import asdict
from datetime import datetime
from uuid import UUID

import aio_pika

from src.domain.events.customer_events import DomainEvent

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = "domain.events"


class EventPublisher:
    """
    Publica eventos de dominio a RabbitMQ.
    Mantiene una conexión persistente y la reconecta si se pierde.
    """

    def __init__(self):
        self._connection = None
        self._channel = None

    async def connect(self):
        """Establece conexión con RabbitMQ."""
        try:
            self._connection = await aio_pika.connect_robust(RABBITMQ_URL)
            self._channel = await self._connection.channel()
            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            self._connection = None
            self._channel = None

    async def disconnect(self):
        """Cierra la conexión con RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("Disconnected from RabbitMQ")

    def _serialize(self, obj):
        """Serializa objetos especiales a JSON."""
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    async def publish(self, event: DomainEvent):
        """
        Publica un evento de dominio al exchange 'domain.events'.

        El evento se serializa a JSON y se envía con la routing key
        correspondiente (ej: 'customer.created'). RabbitMQ enruta el
        mensaje a las queues que tengan bindings matching.

        Args:
            event: Evento de dominio a publicar
        """
        if not self._channel or self._channel.is_closed:
            await self.connect()

        if not self._channel:
            logger.warning(
                f"Cannot publish event {event.event_type}: RabbitMQ not available"
            )
            return

        try:
            # Obtener referencia al exchange (debe existir por la configuración IaC)
            exchange = await self._channel.get_exchange(EXCHANGE_NAME)

            # Serializar el evento completo a JSON
            event_data = asdict(event)
            body = json.dumps(event_data, default=self._serialize).encode()

            # Publicar con la routing key del tipo de evento.
            # RabbitMQ usa esta key para enrutar a las queues correctas.
            message = aio_pika.Message(
                body=body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                headers={
                    "event_type": event.event_type,
                    "correlation_id": event.correlation_id or "",
                    "aggregate_type": event.aggregate_type,
                },
            )

            await exchange.publish(message, routing_key=event.event_type)

            logger.info(
                f"Published event: {event.event_type}",
                extra={
                    "event_id": str(event.event_id),
                    "aggregate_id": str(event.aggregate_id),
                    "correlation_id": event.correlation_id,
                },
            )

        except Exception as e:
            # RESILIENCIA: si falla la publicación, logueamos pero NO
            # hacemos rollback de la operación principal.
            # En producción, usaríamos Transactional Outbox para garantizar
            # que el evento se publique eventualmente.
            logger.error(
                f"Failed to publish event {event.event_type}: {e}",
                extra={"event_id": str(event.event_id)},
            )
