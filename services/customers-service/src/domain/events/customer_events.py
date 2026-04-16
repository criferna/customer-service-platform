"""
=============================================================================
CAPA DE DOMINIO - Eventos de Dominio (Domain Events)
=============================================================================
Un Evento de Dominio representa algo que OCURRIÓ en el dominio de negocio.
Son inmutables (ya pasaron) y se nombran en pasado: "customer.created".

PATRÓN: Event-Driven Architecture
  Cuando ocurre algo relevante en este Bounded Context, se publica un evento.
  Otros servicios pueden reaccionar a estos eventos sin acoplamiento directo.

  Ejemplo de flujo:
    1. Se crea un cliente → se publica "customer.created"
    2. tickets-service recibe el evento y guarda una copia local del cliente
    3. notifications-service podría enviar un email de bienvenida

PATRÓN: Consistencia Eventual
  Los eventos viajan por RabbitMQ de forma asíncrona. Puede haber un delay
  de milisegundos a segundos antes de que otros servicios se enteren.

REFERENCIA: Slide 46 - Event Bus en la arquitectura tipo
=============================================================================
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """
    Clase base para todos los eventos de dominio.
    frozen=True porque los eventos son INMUTABLES (ya ocurrieron, no se modifican).
    """

    # Identificador único del evento (para idempotencia y tracing)
    event_id: UUID = field(default_factory=uuid4)

    # Tipo del evento (routing key en RabbitMQ)
    event_type: str = ""

    # Timestamp de cuándo ocurrió el evento
    occurred_at: datetime = field(default_factory=datetime.utcnow)

    # Correlation ID para tracing distribuido entre servicios.
    # Si una acción en un servicio genera eventos que otros servicios procesan,
    # todos comparten el mismo correlation_id. Esto permite rastrear
    # toda la cadena de eventos en los logs (Observabilidad - Slide 20).
    correlation_id: Optional[str] = None

    # ID del agregado que generó el evento
    aggregate_id: Optional[UUID] = None

    # Tipo del agregado
    aggregate_type: str = "Customer"

    # Datos del evento
    payload: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CustomerCreated(DomainEvent):
    """Evento: Se creó un nuevo cliente."""
    event_type: str = "customer.created"
    aggregate_type: str = "Customer"


@dataclass(frozen=True)
class CustomerUpdated(DomainEvent):
    """Evento: Se actualizaron datos de un cliente."""
    event_type: str = "customer.updated"
    aggregate_type: str = "Customer"


@dataclass(frozen=True)
class CustomerDeleted(DomainEvent):
    """Evento: Se eliminó un cliente (soft delete)."""
    event_type: str = "customer.deleted"
    aggregate_type: str = "Customer"
