# =============================================================================
# PATRON: FACTORY (Creacional)
# =============================================================================
# QUÉ ES:
#   Define una interfaz para crear objetos, pero delega en la lógica de
#   negocio la decisión de qué clase concreta instanciar. El cliente no
#   necesita conocer las clases concretas — solo la interfaz común.
#
# POR QUÉ SE USA AQUÍ:
#   El servicio de notificaciones necesita enviar notificaciones por
#   diferentes canales (Email, SNS, Internal log). En vez de tener
#   if/elif/else en el consumer, un NotificationFactory decide qué
#   tipo de notificador crear según la configuración del entorno.
#
#   Esto permite:
#     - Agregar nuevos canales (SMS, Push, Slack) sin modificar el consumer
#     - Cambiar el canal por configuración (variable de entorno)
#     - Testear con un InternalNotifier sin enviar emails reales
#
# CUÁNDO USARLO EN PRODUCCIÓN:
#   - Cuando el tipo de objeto depende de configuración runtime (env, feature flags)
#   - Cuando hay múltiples implementaciones de una misma interfaz
#   - Cuando quieres desacoplar la creación de la lógica de uso
#   - Procesadores de diferentes tipos de mensaje/evento
#   - Adaptadores de BD según ambiente (DynamoDB local vs AWS)
#
# CUÁNDO NO USARLO:
#   - Si solo hay una implementación y no se prevén más
#   - Si la creación es trivial (un simple constructor basta)
# =============================================================================

import json
import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Interfaz común (Abstract Product)
# ---------------------------------------------------------------------------
class Notifier(ABC):
    """
    Interfaz que todos los notificadores deben implementar.
    Define el contrato: todos saben "enviar" una notificación.
    """

    @abstractmethod
    def send(self, recipient: str, subject: str, body: str, metadata: dict = None) -> dict:
        """
        Envía una notificación.

        Args:
            recipient: Email o ID del destinatario
            subject: Asunto de la notificación
            body: Cuerpo del mensaje
            metadata: Datos adicionales (event_type, correlation_id, etc.)

        Returns:
            dict con resultado del envío (status, message_id, etc.)
        """
        pass


# ---------------------------------------------------------------------------
# Implementaciones concretas (Concrete Products)
# ---------------------------------------------------------------------------
class InternalNotifier(Notifier):
    """
    Notificador interno: solo registra en logs (para desarrollo/lab).
    No envía nada externamente — útil para testing y desarrollo.
    """

    def send(self, recipient: str, subject: str, body: str, metadata: dict = None) -> dict:
        logger.info(
            f"[INTERNAL] Notification sent",
            extra={
                "recipient": recipient,
                "subject": subject,
                "channel": "INTERNAL",
                "event_type": (metadata or {}).get("event_type", ""),
            },
        )
        return {"status": "sent", "channel": "INTERNAL", "recipient": recipient}


class EmailNotifier(Notifier):
    """
    Notificador por email usando Amazon SES.
    En el lab simulamos el envío (SES requiere verificación de dominio).
    En producción, esto enviaría emails reales.
    """

    def __init__(self):
        self.sender = os.environ.get("EMAIL_SENDER", "noreply@lab-ms.example.com")

    def send(self, recipient: str, subject: str, body: str, metadata: dict = None) -> dict:
        # En producción: boto3.client('ses').send_email(...)
        logger.info(
            f"[EMAIL] Would send email",
            extra={
                "from": self.sender,
                "to": recipient,
                "subject": subject,
                "channel": "EMAIL",
            },
        )
        return {"status": "sent", "channel": "EMAIL", "recipient": recipient}


class SnsNotifier(Notifier):
    """
    Notificador via SNS (push notification a un topic dedicado).
    Útil para fan-out de notificaciones a múltiples suscriptores.
    """

    def __init__(self):
        from shared.singleton import SNSClient

        self.sns = SNSClient()
        self.topic_arn = os.environ.get("NOTIFICATIONS_TOPIC_ARN", "")

    def send(self, recipient: str, subject: str, body: str, metadata: dict = None) -> dict:
        if not self.topic_arn:
            logger.warning("NOTIFICATIONS_TOPIC_ARN not configured, falling back to log")
            return {"status": "skipped", "channel": "SNS", "reason": "no topic ARN"}

        message = json.dumps({
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "metadata": metadata or {},
        })
        response = self.sns.publish(topic_arn=self.topic_arn, message=message)
        return {
            "status": "sent",
            "channel": "SNS",
            "message_id": response.get("MessageId", ""),
        }


# ---------------------------------------------------------------------------
# Factory (Creator)
# ---------------------------------------------------------------------------
class NotificationFactory:
    """
    Factory que crea el notificador apropiado según la configuración.

    El canal se configura via variable de entorno NOTIFICATION_CHANNEL.
    Valores posibles: INTERNAL, EMAIL, SNS (default: INTERNAL).

    Uso:
        notifier = NotificationFactory.create()
        notifier.send("maria@test.cl", "Ticket creado", "Tu ticket fue recibido")

    Para agregar un nuevo canal (ej: Slack):
        1. Crear clase SlackNotifier(Notifier)
        2. Agregar "SLACK" al diccionario _notifiers
        3. Listo — el consumer no cambia.
    """

    # Registro de notificadores disponibles
    _notifiers = {
        "INTERNAL": InternalNotifier,
        "EMAIL": EmailNotifier,
        "SNS": SnsNotifier,
    }

    @classmethod
    def create(cls, channel: str = None) -> Notifier:
        """
        Crea un notificador según el canal especificado.

        Args:
            channel: Canal de notificación. Si no se especifica,
                     usa la variable de entorno NOTIFICATION_CHANNEL.

        Returns:
            Instancia de Notifier del tipo apropiado.

        Raises:
            ValueError: Si el canal no está soportado.
        """
        channel = channel or os.environ.get("NOTIFICATION_CHANNEL", "INTERNAL")
        channel = channel.upper()

        notifier_class = cls._notifiers.get(channel)
        if notifier_class is None:
            supported = ", ".join(cls._notifiers.keys())
            raise ValueError(
                f"Canal '{channel}' no soportado. Opciones: {supported}"
            )

        logger.info(f"NotificationFactory: creating {channel} notifier")
        return notifier_class()

    @classmethod
    def register(cls, channel: str, notifier_class: type):
        """
        Registra un nuevo tipo de notificador (extensibilidad).
        Permite agregar canales sin modificar el Factory.
        """
        cls._notifiers[channel.upper()] = notifier_class
