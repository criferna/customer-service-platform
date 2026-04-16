"""
=============================================================================
CAPA DE DOMINIO - Entidad Notification
=============================================================================
Representa una notificación generada por un evento del sistema.

PATRÓN: Event Consumer
  Este servicio NO recibe requests de usuarios directamente.
  Su trabajo principal es consumir eventos de RabbitMQ y generar
  notificaciones automáticas. Ejemplo:
    - ticket.created → Notificar al cliente que su ticket fue recibido
    - ticket.assigned → Notificar al agente y al cliente
    - ticket.resolved → Notificar al cliente que su ticket fue resuelto

Para el laboratorio, las notificaciones se registran en BD y se loguean.
En producción, se integraría con servicios de email, SMS, push, etc.
=============================================================================
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class NotificationChannel(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    INTERNAL = "INTERNAL"


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DELIVERED = "DELIVERED"


class RecipientType(str, Enum):
    CUSTOMER = "CUSTOMER"
    AGENT = "AGENT"


@dataclass
class Notification:
    """Entidad Notification - generada automáticamente por eventos."""

    id: UUID = field(default_factory=uuid4)
    event_type: str = ""
    recipient_id: UUID = field(default_factory=uuid4)
    recipient_type: RecipientType = RecipientType.CUSTOMER
    recipient_email: Optional[str] = None
    channel: NotificationChannel = NotificationChannel.INTERNAL
    subject: str = ""
    body: str = ""
    status: NotificationStatus = NotificationStatus.PENDING
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    source_event_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def mark_sent(self):
        """Marca la notificación como enviada."""
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.utcnow()

    def mark_failed(self, error: str):
        """Marca la notificación como fallida."""
        self.status = NotificationStatus.FAILED
        self.error_message = error
