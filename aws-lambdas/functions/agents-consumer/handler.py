"""
Agents Consumer Lambda.

Triggered by SQS queue: lab-ms-agents-ticket-events
Receives ticket domain events and updates agent workload counters.

Processing:
  - ticket.assigned:  Increment active_tickets_count. If >= max_tickets, set BUSY.
  - ticket.resolved:  Decrement active_tickets_count. If was BUSY and now < max, set ONLINE.
  - ticket.closed:    Same as resolved.

Uses DynamoDB atomic counters (SET active_tickets_count = active_tickets_count + :val)
to avoid race conditions when multiple events are processed concurrently.

Event flow:
  [Tickets Lambda] -> [SNS topic] -> [SQS: lab-ms-agents-ticket-events] -> [This Lambda]
"""

import json
import logging

from shared.singleton import DynamoDBClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Singleton: DynamoDB client
# ---------------------------------------------------------------------------
db = DynamoDBClient()
agents_table = db.table("lab-ms-agents")

# Default max tickets per agent if not stored on the agent record
DEFAULT_MAX_TICKETS = 5


# ---------------------------------------------------------------------------
# Handler (SQS batch processor)
# ---------------------------------------------------------------------------
def handler(event, context):
    """
    Process a batch of SQS records containing ticket events.
    Returns batchItemFailures for partial failure reporting.
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

    return {
        "batchItemFailures": [
            {"itemIdentifier": mid} for mid in failed_message_ids
        ]
    }


# ---------------------------------------------------------------------------
# Record processing
# ---------------------------------------------------------------------------
def _process_record(record: dict) -> None:
    """Parse SQS -> SNS -> event payload and dispatch."""
    sns_message = json.loads(record["body"])
    event_payload = json.loads(sns_message["Message"])

    event_type = event_payload.get("event_type", "")
    payload = event_payload.get("payload", {})
    correlation_id = event_payload.get("correlation_id", "")

    logger.info(json.dumps({
        "message": f"Processing event: {event_type}",
        "event_id": event_payload.get("event_id", ""),
        "correlation_id": correlation_id,
    }))

    if event_type == "ticket.assigned":
        _handle_ticket_assigned(payload)
    elif event_type in ("ticket.resolved", "ticket.closed"):
        _handle_ticket_released(payload, event_type)
    else:
        logger.warning(f"Unhandled event type: {event_type}, skipping")


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------
def _handle_ticket_assigned(payload: dict) -> None:
    """
    ticket.assigned: Increment active_tickets_count for the assigned agent.
    If count reaches max_tickets, set agent status to BUSY.

    Uses atomic counter to prevent race conditions.
    """
    agent_id = payload.get("assigned_agent_id", "")
    if not agent_id:
        logger.warning("ticket.assigned event missing assigned_agent_id, skipping")
        return

    logger.info(f"Incrementing active_tickets_count for agent {agent_id}")

    # Atomic increment and return the new value
    result = agents_table.update_item(
        Key={"id": agent_id},
        UpdateExpression="SET active_tickets_count = if_not_exists(active_tickets_count, :zero) + :inc",
        ExpressionAttributeValues={
            ":inc": 1,
            ":zero": 0,
        },
        ReturnValues="ALL_NEW",
    )

    updated_agent = result.get("Attributes", {})
    active_count = int(updated_agent.get("active_tickets_count", 0))
    max_tickets = int(updated_agent.get("max_tickets", DEFAULT_MAX_TICKETS))
    current_status = updated_agent.get("status", "")

    logger.info(
        f"Agent {agent_id}: active_tickets_count={active_count}, "
        f"max_tickets={max_tickets}, status={current_status}"
    )

    # If agent has reached capacity, set status to BUSY
    if active_count >= max_tickets and current_status != "BUSY":
        agents_table.update_item(
            Key={"id": agent_id},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "BUSY"},
        )
        logger.info(f"Agent {agent_id} set to BUSY (active={active_count}, max={max_tickets})")


def _handle_ticket_released(payload: dict, event_type: str) -> None:
    """
    ticket.resolved / ticket.closed: Decrement active_tickets_count.
    If agent was BUSY and now has capacity, set status back to ONLINE.

    Uses atomic counter with a condition to prevent going below zero.
    """
    agent_id = payload.get("assigned_agent_id", "")
    if not agent_id:
        logger.warning(f"{event_type} event missing assigned_agent_id, skipping")
        return

    logger.info(f"Decrementing active_tickets_count for agent {agent_id} ({event_type})")

    # Atomic decrement, but only if count > 0 to avoid negative values
    try:
        result = agents_table.update_item(
            Key={"id": agent_id},
            UpdateExpression="SET active_tickets_count = active_tickets_count - :dec",
            ConditionExpression="attribute_exists(active_tickets_count) AND active_tickets_count > :zero",
            ExpressionAttributeValues={
                ":dec": 1,
                ":zero": 0,
            },
            ReturnValues="ALL_NEW",
        )
    except agents_table.meta.client.exceptions.ConditionalCheckFailedException:
        logger.warning(
            f"Agent {agent_id}: active_tickets_count is already 0 or does not exist, "
            "skipping decrement"
        )
        return

    updated_agent = result.get("Attributes", {})
    active_count = int(updated_agent.get("active_tickets_count", 0))
    max_tickets = int(updated_agent.get("max_tickets", DEFAULT_MAX_TICKETS))
    current_status = updated_agent.get("status", "")

    logger.info(
        f"Agent {agent_id}: active_tickets_count={active_count}, "
        f"max_tickets={max_tickets}, status={current_status}"
    )

    # If agent was BUSY and now has capacity, set back to ONLINE
    if current_status == "BUSY" and active_count < max_tickets:
        agents_table.update_item(
            Key={"id": agent_id},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "ONLINE"},
        )
        logger.info(f"Agent {agent_id} set back to ONLINE (active={active_count}, max={max_tickets})")
