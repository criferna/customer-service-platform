"""
Agents API Lambda Handler.

Manages support agents with Strategy pattern for agent assignment.
Uses API Gateway proxy integration.

Routes:
    GET    /api/v1/agents                - List agents
    POST   /api/v1/agents                - Create agent
    GET    /api/v1/agents/{id}           - Get agent by ID
    PUT    /api/v1/agents/{id}           - Update agent
    PUT    /api/v1/agents/{id}/status    - Change agent status
    GET    /api/v1/agents/available/next - Get next available agent (Strategy pattern)
"""

import time
import uuid

from shared.decorator import lambda_handler, response
from shared.singleton import DynamoDBClient
from shared.observer import DomainEventPublisher
from shared.strategy import AgentAssignmentContext

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TABLE_NAME = "lab-ms-agents"
VALID_STATUSES = {"ONLINE", "OFFLINE", "BUSY", "ON_BREAK"}

# ---------------------------------------------------------------------------
# Singletons (initialized once per Lambda container)
# ---------------------------------------------------------------------------
db = DynamoDBClient()
table = db.table(TABLE_NAME)
publisher = DomainEventPublisher()
assignment_context = AgentAssignmentContext()


# ---------------------------------------------------------------------------
# Route helpers
# ---------------------------------------------------------------------------
def _parse_route(event):
    """
    Parse the HTTP method and path to determine the route.

    Returns:
        tuple: (action, agent_id)
            action: one of "list", "create", "get", "update",
                    "change_status", "next_available"
            agent_id: str or None
    """
    method = event.get("httpMethod", "GET")
    path = event.get("path", "")
    path_params = event.get("pathParameters") or {}

    # Normalize: strip trailing slash
    path = path.rstrip("/")
    segments = path.split("/")
    # Expected: ["", "api", "v1", "agents", ...]

    # GET /api/v1/agents/available/next
    if method == "GET" and len(segments) == 6 and segments[4] == "available" and segments[5] == "next":
        return "next_available", None

    if method == "GET" and len(segments) == 4:
        # GET /api/v1/agents
        return "list", None

    if method == "POST" and len(segments) == 4:
        # POST /api/v1/agents
        return "create", None

    if method == "GET" and len(segments) == 5:
        # GET /api/v1/agents/{id}
        agent_id = path_params.get("id") or segments[4]
        return "get", agent_id

    if method == "PUT" and len(segments) == 6 and segments[5] == "status":
        # PUT /api/v1/agents/{id}/status
        agent_id = path_params.get("id") or segments[4]
        return "change_status", agent_id

    if method == "PUT" and len(segments) == 5:
        # PUT /api/v1/agents/{id}
        agent_id = path_params.get("id") or segments[4]
        return "update", agent_id

    raise ValueError(f"Unsupported route: {method} {path}")


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _get_agent(agent_id):
    """Fetch an agent by ID. Raises KeyError if not found."""
    result = table.get_item(Key={"id": agent_id})
    item = result.get("Item")
    if not item:
        raise KeyError(agent_id)
    return item


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------
def _list_agents(event):
    result = table.scan()
    agents = result.get("Items", [])
    return response(200, {"agents": agents, "count": len(agents)})


def _create_agent(event):
    body = event.get("parsed_body", {})

    # Validate required fields
    first_name = body.get("first_name")
    last_name = body.get("last_name")
    email = body.get("email")
    if not first_name:
        raise ValueError("Field 'first_name' is required")
    if not last_name:
        raise ValueError("Field 'last_name' is required")
    if not email:
        raise ValueError("Field 'email' is required")

    now = _now()
    agent_id = str(uuid.uuid4())

    agent = {
        "id": agent_id,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "status": body.get("status", "OFFLINE"),
        "max_tickets": body.get("max_tickets", 5),
        "active_tickets_count": 0,
        "skills": body.get("skills", []),
        "created_at": now,
        "updated_at": now,
    }

    # Validate initial status if provided
    if agent["status"] not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{agent['status']}'. Valid statuses: {sorted(VALID_STATUSES)}"
        )

    table.put_item(Item=agent)

    return response(201, agent)


def _get_agent_handler(agent_id):
    agent = _get_agent(agent_id)
    return response(200, agent)


def _update_agent(event, agent_id):
    body = event.get("parsed_body", {})
    correlation_id = event.get("correlation_id", "")

    # Ensure agent exists
    agent = _get_agent(agent_id)

    # Build dynamic update expression from allowed fields
    allowed_fields = {"first_name", "last_name", "email", "max_tickets", "skills"}
    update_parts = ["updated_at = :now"]
    expr_values = {":now": _now()}
    expr_names = {}

    for field in allowed_fields:
        if field in body:
            placeholder = f":{field}"
            update_parts.append(f"#{field} = {placeholder}")
            expr_values[placeholder] = body[field]
            expr_names[f"#{field}"] = field

    if len(update_parts) == 1:
        raise ValueError("No valid fields provided for update")

    table.update_item(
        Key={"id": agent_id},
        UpdateExpression="SET " + ", ".join(update_parts),
        ExpressionAttributeValues=expr_values,
        ExpressionAttributeNames=expr_names if expr_names else None,
    )

    # Re-fetch to return updated agent
    updated_agent = _get_agent(agent_id)

    publisher.publish(
        event_type="agent.updated",
        aggregate_id=agent_id,
        payload=updated_agent,
        correlation_id=correlation_id,
    )

    return response(200, updated_agent)


def _change_status(event, agent_id):
    body = event.get("parsed_body", {})
    correlation_id = event.get("correlation_id", "")

    new_status = body.get("status")
    if not new_status:
        raise ValueError("Field 'status' is required")

    new_status = new_status.upper()
    if new_status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{new_status}'. Valid statuses: {sorted(VALID_STATUSES)}"
        )

    # Ensure agent exists
    agent = _get_agent(agent_id)
    old_status = agent.get("status")

    if old_status == new_status:
        return response(200, agent)

    now = _now()
    table.update_item(
        Key={"id": agent_id},
        UpdateExpression="SET #s = :status, updated_at = :now",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":status": new_status, ":now": now},
    )

    agent["status"] = new_status
    agent["updated_at"] = now

    publisher.publish(
        event_type="agent.status_changed",
        aggregate_id=agent_id,
        payload={
            **agent,
            "previous_status": old_status,
            "new_status": new_status,
        },
        correlation_id=correlation_id,
    )

    return response(200, agent)


def _next_available(event):
    """
    Get the next available agent using the Strategy pattern.

    Queries agents with status=ONLINE via the status-index GSI,
    filters to those with capacity (active_tickets_count < max_tickets),
    then delegates selection to AgentAssignmentContext.
    """
    query_params = event.get("queryStringParameters") or {}
    category = query_params.get("category", "")

    # Query ONLINE agents from the status-index GSI
    result = table.query(
        IndexName="status-index",
        KeyConditionExpression="#s = :online",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":online": "ONLINE"},
    )

    agents = result.get("Items", [])

    # Filter agents with available capacity
    available = [
        a for a in agents
        if int(a.get("active_tickets_count", 0)) < int(a.get("max_tickets", 5))
    ]

    if not available:
        return response(404, {
            "error": "No available agents",
            "strategy": assignment_context.current_strategy,
        })

    # Build a pseudo-ticket dict for the strategy (used by SkillBasedStrategy)
    ticket_context = {"category": category} if category else {}

    selected = assignment_context.assign(available, ticket_context)

    if not selected:
        return response(404, {
            "error": "No suitable agent found by strategy",
            "strategy": assignment_context.current_strategy,
        })

    return response(200, {
        "agent": selected,
        "strategy": assignment_context.current_strategy,
    })


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------
@lambda_handler()
def handler(event, context):
    action, agent_id = _parse_route(event)

    if action == "list":
        return _list_agents(event)

    if action == "create":
        return _create_agent(event)

    if action == "get":
        return _get_agent_handler(agent_id)

    if action == "update":
        return _update_agent(event, agent_id)

    if action == "change_status":
        return _change_status(event, agent_id)

    if action == "next_available":
        return _next_available(event)
