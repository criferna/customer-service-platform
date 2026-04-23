"""
Notifications Consumer Lambda.

Triggered by SQS queue: lab-ms-notifications-ticket-events
Receives ticket domain events and creates notifications for the relevant
customer, then sends them via the configured notification channel.

Design patterns used:
  - Factory: NotificationFactory selects the delivery channel at runtime
  - Singleton: DynamoDBClient reused across warm invocations
  - Idempotency: source_event_id checked before processing to avoid duplicates

Event flow:
  [Tickets Lambda] -> [SNS topic] -> [SQS queue] -> [This Lambda]

Each SQS record body is an SNS notification JSON whose "Message" field
contains the actual domain event payload.
"""

import json
import logging
import time
import uuid

from shared.singleton import DynamoDBClient
from shared.factory import NotificationFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Singleton: DynamoDB client
# ---------------------------------------------------------------------------
db = DynamoDBClient()
table = db.table("lab-ms-notifications")

# ---------------------------------------------------------------------------
# Notification templates per event type
# ---------------------------------------------------------------------------
TEMPLATES = {
    "ticket.created": {
        "subject": "Tu ticket #{short_id} ha sido recibido",
        "body": (
            "Hemos recibido tu ticket #{short_id}. "
            "Nuestro equipo lo revisara a la brevedad. "
            "Titulo: {title}"
        ),
    },
    "ticket.assigned": {
        "subject": "Tu ticket #{short_id} ha sido asignado",
        "body": (
            "Tu ticket #{short_id} ha sido asignado a un agente "
            "y esta siendo atendido. Titulo: {title}"
        ),
    },
    "ticket.resolved": {
        "subject": "Tu ticket #{short_id} ha sido resuelto",
        "body": (
            "Tu ticket #{short_id} ha sido marcado como resuelto. "
            "Si el problema persiste, puedes reabrir el ticket. "
            "Titulo: {title}"
        ),
    },
    "ticket.closed": {
        "subject": "Tu ticket #{short_id} ha sido cerrado",
        "body": (
            "Tu ticket #{short_id} ha sido cerrado definitivamente. "
            "Gracias por contactarnos. Titulo: {title}"
        ),
    },
}


# ---------------------------------------------------------------------------
# Handler (SQS batch processor -- no HTTP decorator needed)
# ---------------------------------------------------------------------------
def handler(event, context):
    """
    Process a batch of SQS records. Each record contains an SNS message
    wrapping a ticket domain event.

    Returns a batchItemFailures list so that only failed records are retried.
    """
    failed_message_ids = []

    for record in event.get("Records", []):
        message_id = record.get("messageId", "")
        try:
            _process_record(record)
        except Exception as exc:
            logger.error(
                f"Failed to process record {message_id}: {exc}",
                exc_info=True,
            )
            failed_message_ids.append(message_id)

    # Partial batch failure reporting
    return {
        "batchItemFailures": [
            {"itemIdentifier": mid} for mid in failed_message_ids
        ]
    }


# ---------------------------------------------------------------------------
# Record processing
# ---------------------------------------------------------------------------
def _process_record(record: dict) -> None:
    """Parse SQS -> SNS -> event payload and create a notification."""
    # 1. Parse SQS record body (SNS envelope)
    sns_message = json.loads(record["body"])
    event_payload = json.loads(sns_message["Message"])

    event_type = event_payload.get("event_type", "")
    event_id = event_payload.get("event_id", "")
    payload = event_payload.get("payload", {})
    correlation_id = event_payload.get("correlation_id", "")

    logger.info(json.dumps({
        "message": f"Processing event: {event_type}",
        "event_id": event_id,
        "correlation_id": correlation_id,
    }))

    # 2. Validate event type
    template = TEMPLATES.get(event_type)
    if not template:
        logger.warning(f"Unknown event type: {event_type}, skipping")
        return

    # 3. Idempotency check: skip if a notification for this event already exists
    if _notification_exists(event_id):
        logger.info(f"Notification for event {event_id} already exists, skipping (idempotent)")
        return

    # 4. Build notification content from template
    ticket_id = payload.get("id", "")
    short_id = ticket_id[:8] if ticket_id else "unknown"
    title = payload.get("title", "Sin titulo")

    subject = template["subject"].format(short_id=short_id, title=title)
    body = template["body"].format(short_id=short_id, title=title)

    recipient_id = payload.get("customer_id", "")
    recipient_email = payload.get("customer_email", "")

    # 5. Persist notification in DynamoDB
    notification_id = str(uuid.uuid4())
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    notifier = NotificationFactory.create()

    notification_item = {
        "id": notification_id,
        "event_type": event_type,
        "recipient_id": recipient_id,
        "recipient_type": "customer",
        "recipient_email": recipient_email,
        "channel": notifier.__class__.__name__.replace("Notifier", "").upper(),
        "subject": subject,
        "body": body,
        "status": "PENDING",
        "source_event_id": event_id,
        "created_at": now,
    }

    table.put_item(Item=notification_item)
    logger.info(f"Notification {notification_id} saved for event {event_id}")

    # 6. Send notification via the configured channel (Factory pattern)
    try:
        result = notifier.send(
            recipient=recipient_email or recipient_id,
            subject=subject,
            body=body,
            metadata={
                "event_type": event_type,
                "notification_id": notification_id,
                "correlation_id": correlation_id,
                "ticket_id": ticket_id,
            },
        )
        # Update status to SENT
        table.update_item(
            Key={"id": notification_id},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "SENT"},
        )
        logger.info(f"Notification {notification_id} sent via {result.get('channel', 'UNKNOWN')}")
    except Exception as send_err:
        # Update status to FAILED but do not re-raise -- the notification
        # was persisted; delivery can be retried separately.
        logger.error(f"Failed to send notification {notification_id}: {send_err}")
        table.update_item(
            Key={"id": notification_id},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "FAILED"},
        )


def _notification_exists(source_event_id: str) -> bool:
    """
    Check if a notification has already been created for this event.
    Uses a scan with filter on source_event_id.
    """
    from boto3.dynamodb.conditions import Attr

    result = table.scan(
        FilterExpression=Attr("source_event_id").eq(source_event_id),
        Limit=1,
        ProjectionExpression="id",
    )
    return len(result.get("Items", [])) > 0
