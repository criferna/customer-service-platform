"""
Tickets Consumer Lambda.

Triggered by two SQS queues:
  - lab-ms-tickets-customer-events: customer.created, customer.updated, customer.deleted
  - lab-ms-tickets-agent-events: agent.updated

Maintains denormalized data consistency in the lab-ms-tickets table.
When a customer or agent is updated, this consumer propagates name/email
changes to all tickets referencing that entity.

Event flow:
  [Customers Lambda] -> [SNS] -> [SQS: customer-events] -> [This Lambda]
  [Agents Lambda]    -> [SNS] -> [SQS: agent-events]     -> [This Lambda]
"""

import json
import logging

from boto3.dynamodb.conditions import Attr

from shared.singleton import DynamoDBClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Singleton: DynamoDB client
# ---------------------------------------------------------------------------
db = DynamoDBClient()
tickets_table = db.table("lab-ms-tickets")


# ---------------------------------------------------------------------------
# Handler (SQS batch processor)
# ---------------------------------------------------------------------------
def handler(event, context):
    """
    Process a batch of SQS records containing customer or agent events.
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
    """Parse SQS -> SNS -> event payload and dispatch to the appropriate handler."""
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

    if event_type == "customer.updated":
        _handle_customer_updated(payload)
    elif event_type == "customer.deleted":
        _handle_customer_deleted(payload)
    elif event_type == "customer.created":
        _handle_customer_created(payload)
    elif event_type == "agent.updated":
        _handle_agent_updated(payload)
    else:
        logger.warning(f"Unhandled event type: {event_type}, skipping")


# ---------------------------------------------------------------------------
# Customer event handlers
# ---------------------------------------------------------------------------
def _handle_customer_created(payload: dict) -> None:
    """
    customer.created: No action needed on tickets table.
    A new customer has no tickets yet.
    """
    logger.info(
        f"Customer created: {payload.get('id', 'unknown')}. "
        "No ticket updates required."
    )


def _handle_customer_updated(payload: dict) -> None:
    """
    customer.updated: Update denormalized customer_name and customer_email
    in all tickets belonging to this customer.

    Uses scan + filter (acceptable for lab-scale data) then batch updates.
    """
    customer_id = payload.get("id", "")
    new_name = payload.get("name", "")
    new_email = payload.get("email", "")

    if not customer_id:
        logger.warning("customer.updated event missing customer id, skipping")
        return

    # Find all tickets for this customer
    tickets = _scan_tickets_by_field("customer_id", customer_id)

    if not tickets:
        logger.info(f"No tickets found for customer {customer_id}, nothing to update")
        return

    logger.info(f"Updating {len(tickets)} ticket(s) for customer {customer_id}")

    # Build update expression dynamically based on available fields
    update_parts = []
    expression_values = {}
    expression_names = {}

    if new_name:
        update_parts.append("#cn = :cn")
        expression_names["#cn"] = "customer_name"
        expression_values[":cn"] = new_name

    if new_email:
        update_parts.append("#ce = :ce")
        expression_names["#ce"] = "customer_email"
        expression_values[":ce"] = new_email

    if not update_parts:
        logger.info("No name or email changes detected, skipping")
        return

    update_expression = "SET " + ", ".join(update_parts)

    for ticket in tickets:
        ticket_id = ticket["id"]
        try:
            tickets_table.update_item(
                Key={"id": ticket_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
            )
            logger.info(f"Updated ticket {ticket_id} with new customer data")
        except Exception as e:
            logger.error(f"Failed to update ticket {ticket_id}: {e}")
            raise


def _handle_customer_deleted(payload: dict) -> None:
    """
    customer.deleted: Log the event. Tickets keep historical data and are
    NOT deleted -- they serve as audit/history records.
    """
    customer_id = payload.get("id", "unknown")
    logger.info(
        f"Customer {customer_id} deleted. "
        "Tickets preserved for historical records (no changes applied)."
    )


# ---------------------------------------------------------------------------
# Agent event handlers
# ---------------------------------------------------------------------------
def _handle_agent_updated(payload: dict) -> None:
    """
    agent.updated: Update denormalized assigned_agent_name in all tickets
    where assigned_agent_id matches this agent.
    """
    agent_id = payload.get("id", "")
    new_name = payload.get("name", "")

    if not agent_id:
        logger.warning("agent.updated event missing agent id, skipping")
        return

    if not new_name:
        logger.info(f"agent.updated for {agent_id} has no name change, skipping")
        return

    # Find all tickets assigned to this agent
    tickets = _scan_tickets_by_field("assigned_agent_id", agent_id)

    if not tickets:
        logger.info(f"No tickets assigned to agent {agent_id}, nothing to update")
        return

    logger.info(f"Updating {len(tickets)} ticket(s) for agent {agent_id}")

    for ticket in tickets:
        ticket_id = ticket["id"]
        try:
            tickets_table.update_item(
                Key={"id": ticket_id},
                UpdateExpression="SET #aan = :aan",
                ExpressionAttributeNames={"#aan": "assigned_agent_name"},
                ExpressionAttributeValues={":aan": new_name},
            )
            logger.info(f"Updated ticket {ticket_id} with new agent name")
        except Exception as e:
            logger.error(f"Failed to update ticket {ticket_id}: {e}")
            raise


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _scan_tickets_by_field(field_name: str, field_value: str) -> list:
    """
    Scan the tickets table filtering by a specific field.
    Handles pagination for complete results.
    """
    items = []
    params = {
        "FilterExpression": Attr(field_name).eq(field_value),
        "ProjectionExpression": "id",
    }

    while True:
        result = tickets_table.scan(**params)
        items.extend(result.get("Items", []))

        last_key = result.get("LastEvaluatedKey")
        if not last_key:
            break
        params["ExclusiveStartKey"] = last_key

    return items
