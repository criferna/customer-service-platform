# =============================================================================
# PATRON: OBSERVER (Comportamiento)
# =============================================================================
# QUÉ ES:
#   Define una dependencia uno-a-muchos: cuando un objeto (Subject) cambia
#   de estado, todos sus observadores (Observers) son notificados
#   automáticamente. El Subject NO conoce a los Observers concretos.
#
# POR QUÉ SE USA AQUÍ:
#   En la versión Docker, RabbitMQ implementaba el Observer pattern:
#     - tickets-service (Subject) publicaba eventos
#     - notifications-service y agents-service (Observers) reaccionaban
#
#   En AWS, este patrón se mapea naturalmente a SNS + SQS:
#     - SNS Topic = Subject (recibe eventos)
#     - SQS Queues = Observers (suscritos al topic, reciben copia del evento)
#
#   Esta clase implementa el patrón Observer tanto a nivel de aplicación
#   (para uso interno) como wrapper sobre SNS (para comunicación entre
#   servicios).
#
# CUÁNDO USARLO EN PRODUCCIÓN:
#   - Event-driven architectures (pub/sub)
#   - Notificaciones a múltiples interesados
#   - Desacoplamiento entre componentes
#   - Audit logging (observer que registra todo)
#   - Cache invalidation (observer que limpia cache)
#
# CUÁNDO NO USARLO:
#   - Si solo hay un consumidor (llamada directa es más simple)
#   - Si el orden de notificación importa (Observer no garantiza orden)
#   - Si necesitas respuesta sincrónica del observer
# =============================================================================

import json
import logging
import os
import time
import uuid
from abc import ABC, abstractmethod

from shared.singleton import SNSClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Observer Pattern - Implementación a nivel de aplicación
# ---------------------------------------------------------------------------
class EventObserver(ABC):
    """
    Interfaz Observer: define el contrato para recibir eventos.
    Cualquier clase que quiera reaccionar a eventos debe implementar update().
    """

    @abstractmethod
    def update(self, event_type: str, payload: dict) -> None:
        """Llamado cuando ocurre un evento al que el observer está suscrito."""
        pass


class EventSubject:
    """
    Subject: mantiene una lista de observers y los notifica cuando
    ocurren eventos.

    Uso local (dentro de un mismo servicio):
        subject = EventSubject()
        subject.attach("ticket.created", my_observer)
        subject.notify("ticket.created", {"id": "123", ...})

    Cada observer recibe una copia del evento.
    """

    def __init__(self):
        # Diccionario: event_type → lista de observers
        self._observers: dict[str, list[EventObserver]] = {}

    def attach(self, event_type: str, observer: EventObserver) -> None:
        """Suscribe un observer a un tipo de evento."""
        if event_type not in self._observers:
            self._observers[event_type] = []
        if observer not in self._observers[event_type]:
            self._observers[event_type].append(observer)
            logger.info(f"Observer {observer.__class__.__name__} attached to {event_type}")

    def detach(self, event_type: str, observer: EventObserver) -> None:
        """Desuscribe un observer de un tipo de evento."""
        if event_type in self._observers:
            self._observers[event_type] = [
                o for o in self._observers[event_type] if o is not observer
            ]

    def notify(self, event_type: str, payload: dict) -> None:
        """Notifica a todos los observers suscritos a este tipo de evento."""
        observers = self._observers.get(event_type, [])
        for observer in observers:
            try:
                observer.update(event_type, payload)
            except Exception as e:
                logger.error(
                    f"Observer {observer.__class__.__name__} failed: {e}"
                )


# ---------------------------------------------------------------------------
# Observer Pattern - Implementación sobre AWS SNS (comunicación entre servicios)
# ---------------------------------------------------------------------------
class DomainEventPublisher:
    """
    Publisher de eventos de dominio via SNS.

    Implementa el lado "Subject" del Observer pattern usando AWS SNS.
    Cuando un microservicio publica un evento, SNS lo distribuye
    automáticamente a todas las SQS queues suscritas (los Observers).

    Topología AWS:
        [Lambda] → publish() → [SNS Topic: lab-ms-domain-events]
                                    ├→ [SQS: lab-ms-tickets-customer-events]
                                    ├→ [SQS: lab-ms-notifications-ticket-events]
                                    └→ [SQS: lab-ms-agents-ticket-events]

    Cada SQS queue tiene un filtro por event_type, así solo recibe
    los eventos que le interesan (equivalente a routing keys en RabbitMQ).
    """

    def __init__(self, service_name: str = None):
        self.sns = SNSClient()
        self.topic_arn = os.environ.get("DOMAIN_EVENTS_TOPIC_ARN", "")
        self.service_name = service_name or os.environ.get("SERVICE_NAME", "unknown")

    def publish(self, event_type: str, aggregate_id: str, payload: dict,
                correlation_id: str = None) -> dict:
        """
        Publica un evento de dominio al topic SNS.

        Args:
            event_type: Tipo del evento (ej: "ticket.created")
            aggregate_id: ID de la entidad que generó el evento
            payload: Datos del evento
            correlation_id: ID para tracing distribuido

        Returns:
            dict con event_id y message_id de SNS
        """
        event_id = str(uuid.uuid4())
        event = {
            "event_id": event_id,
            "event_type": event_type,
            "aggregate_id": str(aggregate_id),
            "aggregate_type": event_type.split(".")[0].capitalize(),
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "occurred_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_service": self.service_name,
            "payload": payload,
        }

        if not self.topic_arn:
            logger.warning(f"DOMAIN_EVENTS_TOPIC_ARN not set, event {event_type} not published")
            return {"event_id": event_id, "published": False}

        # MessageAttributes permite filtrado en las suscripciones SQS.
        # SNS usa estos atributos para decidir a qué queues enviar.
        # Equivalente a routing keys en RabbitMQ.
        message_attributes = {
            "event_type": {
                "DataType": "String",
                "StringValue": event_type,
            },
            "aggregate_type": {
                "DataType": "String",
                "StringValue": event["aggregate_type"],
            },
        }

        response = self.sns.publish(
            topic_arn=self.topic_arn,
            message=json.dumps(event, default=str),
            message_attributes=message_attributes,
        )

        logger.info(json.dumps({
            "message": f"Published event: {event_type}",
            "event_id": event_id,
            "aggregate_id": str(aggregate_id),
            "correlation_id": event["correlation_id"],
            "sns_message_id": response.get("MessageId", ""),
        }))

        return {
            "event_id": event_id,
            "message_id": response.get("MessageId", ""),
            "published": True,
        }
