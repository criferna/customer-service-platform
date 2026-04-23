"""
Tickets API Lambda Handler.

Manages support ticket lifecycle with State Machine pattern for status transitions.
Uses API Gateway proxy integration.

Routes:
    GET    /api/v1/tickets              - List tickets (optional ?status= filter)
    POST   /api/v1/tickets              - Create ticket
    GET    /api/v1/tickets/{id}         - Get ticket by ID
    PUT    /api/v1/tickets/{id}/assign  - Assign agent to ticket
    PUT    /api/v1/tickets/{id}/start   - Start working on ticket
    PUT    /api/v1/tickets/{id}/resolve - Resolve ticket
    PUT    /api/v1/tickets/{id}/close   - Close ticket
    PUT    /api/v1/tickets/{id}/reopen  - Reopen ticket
"""

import time
import uuid

from shared.decorator import lambda_handler, response
from shared.singleton import DynamoDBClient
from shared.observer import DomainEventPublisher

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TABLE_NAME = "lab-ms-tickets"

# State Machine: valid status transitions
# Each key maps to the set of statuses it can transition TO.
VALID_TRANSITIONS = {
    "OPEN": {"ASSIGNED"},
    "ASSIGNED": {"IN_PROGRESS", "OPEN"},
    "IN_PROGRESS": {"RESOLVED", "ASSIGNED"},
    "RESOLVED": {"CLOSED", "REOPENED"},
    "CLOSED": set(),  # terminal state
    "REOPENED": {"ASSIGNED"},
}

# Action -> target status mapping
ACTION_TARGET_STATUS = {
    "assign": "ASSIGNED",
    "start": "IN_PROGRESS",
    "resolve": "RESOLVED",
    "close": "CLOSED",
    "reopen": "REOPENED",
}

# Required source statuses for each action
ACTION_REQUIRED_SOURCE = {
    "assign": {"OPEN", "REOPENED", "IN_PROGRESS"},
    "start": {"ASSIGNED"},
    "resolve": {"IN_PROGRESS"},
    "close": {"RESOLVED"},
    "reopen": {"RESOLVED"},
}

# ---------------------------------------------------------------------------
# Singletons (initialized once per Lambda container)
# ---------------------------------------------------------------------------
db = DynamoDBClient()
table = db.table(TABLE_NAME)
publisher = DomainEventPublisher()


# ---------------------------------------------------------------------------
# Route helpers
# ---------------------------------------------------------------------------
def _parse_route(event):
    """
    Parse the HTTP method and path to determine the route.

    Returns:
        tuple: (action, ticket_id)
            action: one of "list", "create", "get", "assign", "start",
                    "resolve", "close", "reopen"
            ticket_id: str or None
    """
    method = event.get("httpMethod", "GET")
    path = event.get("path", "")
    path_params = event.get("pathParameters") or {}

    # Normalize: strip trailing slash
    path = path.rstrip("/")
    segments = path.split("/")
    # Expected: ["", "api", "v1", "tickets", ...]

    if method == "GET" and len(segments) == 4:
        # GET /api/v1/tickets
        return "list", None

    if method == "POST" and len(segments) == 4:
        # POST /api/v1/tickets
        return "create", None

    if method == "GET" and len(segments) == 5:
        # GET /api/v1/tickets/{id}
        ticket_id = path_params.get("id") or segments[4]
        return "get", ticket_id

    if method == "PUT" and len(segments) == 6:
        # PUT /api/v1/tickets/{id}/{action}
        ticket_id = path_params.get("id") or segments[4]
        action = segments[5]
        if action in ACTION_TARGET_STATUS:
            return action, ticket_id

    raise ValueError(f"Unsupported route: {method} {path}")


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _validate_transition(current_status, target_status):
    """Validate a state machine transition. Raises ValueError if invalid."""
    allowed = VALID_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise ValueError(
            f"Invalid status transition: {current_status} -> {target_status}. "
            f"Allowed transitions from {current_status}: {sorted(allowed) if allowed else 'none (terminal state)'}"
        )


def _get_ticket(ticket_id):
    """Fetch a ticket by ID. Raises KeyError if not found."""
    result = table.get_item(Key={"id": ticket_id})
    item = result.get("Item")
    if not item:
        raise KeyError(ticket_id)
    return item


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------
def _list_tickets(event):
    query_params = event.get("queryStringParameters") or {}
    status_filter = query_params.get("status")

    if status_filter:
        # Use GSI to query by status
        result = table.query(
            IndexName="status-index",
            KeyConditionExpression="status = :s",
            ExpressionAttributeValues={":s": status_filter.upper()},
            ScanIndexForward=False,
        )
    else:
        result = table.scan()

    tickets = result.get("Items", [])
    return response(200, {"tickets": tickets, "count": len(tickets)})


def _create_ticket(event):
    body = event.get("parsed_body", {})
    correlation_id = event.get("correlation_id", "")

    # Validate required fields
    customer_id = body.get("customer_id")
    subject = body.get("subject")
    if not customer_id:
        raise ValueError("Field 'customer_id' is required")
    if not subject:
        raise ValueError("Field 'subject' is required")

    now = _now()
    ticket_id = str(uuid.uuid4())

    ticket = {
        "id": ticket_id,
        "subject": subject,
        "description": body.get("description", ""),
        "status": "OPEN",
        "priority": body.get("priority", "MEDIUM"),
        "customer_id": customer_id,
        "customer_name": body.get("customer_name", ""),
        "customer_email": body.get("customer_email", ""),
        "assigned_agent_id": None,
        "assigned_agent_name": None,
        "category": body.get("category", "GENERAL"),
        "created_at": now,
        "updated_at": now,
        "assigned_at": None,
        "resolved_at": None,
        "closed_at": None,
    }

    table.put_item(Item=ticket)

    # Publish domain event
    publisher.publish(
        event_type="ticket.created",
        aggregate_id=ticket_id,
        payload=ticket,
        correlation_id=correlation_id,
    )

    return response(201, ticket)


def _get_ticket_handler(ticket_id):
    ticket = _get_ticket(ticket_id)
    return response(200, ticket)


def _assign_ticket(event, ticket_id):
    body = event.get("parsed_body", {})
    correlation_id = event.get("correlation_id", "")

    agent_id = body.get("agent_id")
    agent_name = body.get("agent_name")
    if not agent_id:
        raise ValueError("Field 'agent_id' is required")
    if not agent_name:
        raise ValueError("Field 'agent_name' is required")

    ticket = _get_ticket(ticket_id)
    _validate_transition(ticket["status"], "ASSIGNED")

    now = _now()
    table.update_item(
        Key={"id": ticket_id},
        UpdateExpression=(
            "SET #s = :status, assigned_agent_id = :agent_id, "
            "assigned_agent_name = :agent_name, assigned_at = :now, updated_at = :now"
        ),
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": "ASSIGNED",
            ":agent_id": agent_id,
            ":agent_name": agent_name,
            ":now": now,
        },
    )

    ticket.update({
        "status": "ASSIGNED",
        "assigned_agent_id": agent_id,
        "assigned_agent_name": agent_name,
        "assigned_at": now,
        "updated_at": now,
    })

    publisher.publish(
        event_type="ticket.assigned",
        aggregate_id=ticket_id,
        payload=ticket,
        correlation_id=correlation_id,
    )

    return response(200, ticket)


def _transition_ticket(event, ticket_id, action):
    """Handle simple status transitions (start, resolve, close, reopen)."""
    correlation_id = event.get("correlation_id", "")
    target_status = ACTION_TARGET_STATUS[action]

    ticket = _get_ticket(ticket_id)
    _validate_transition(ticket["status"], target_status)

    now = _now()
    update_expr = "SET #s = :status, updated_at = :now"
    expr_values = {":status": target_status, ":now": now}
    expr_names = {"#s": "status"}

    # Set timestamp fields for specific transitions
    if target_status == "RESOLVED":
        update_expr += ", resolved_at = :now"
    elif target_status == "CLOSED":
        update_expr += ", closed_at = :now"

    table.update_item(
        Key={"id": ticket_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )

    ticket["status"] = target_status
    ticket["updated_at"] = now
    if target_status == "RESOLVED":
        ticket["resolved_at"] = now
    elif target_status == "CLOSED":
        ticket["closed_at"] = now

    # Publish events for resolved and closed transitions
    event_map = {
        "RESOLVED": "ticket.resolved",
        "CLOSED": "ticket.closed",
    }
    event_type = event_map.get(target_status)
    if event_type:
        publisher.publish(
            event_type=event_type,
            aggregate_id=ticket_id,
            payload=ticket,
            correlation_id=correlation_id,
        )

    return response(200, ticket)


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------
@lambda_handler()
def handler(event, context):
    action, ticket_id = _parse_route(event)

    if action == "list":
        return _list_tickets(event)

    if action == "create":
        return _create_ticket(event)

    if action == "get":
        return _get_ticket_handler(ticket_id)

    if action == "assign":
        return _assign_ticket(event, ticket_id)

    # start, resolve, close, reopen
    return _transition_ticket(event, ticket_id, action)
