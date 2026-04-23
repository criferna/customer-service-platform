"""
Notifications API Lambda (read-only).

Exposes REST endpoints for querying notifications stored in DynamoDB.
This Lambda does NOT create notifications -- that is handled by the
notifications-consumer Lambda which reacts to ticket domain events.

DynamoDB Table: lab-ms-notifications
  PK: id (String)
  GSI: recipient-index (recipient_id, created_at)

Routes:
  GET /api/v1/notifications        -- list (supports recipient_id filter, skip/limit)
  GET /api/v1/notifications/{id}   -- get single notification by id
"""

import logging

from shared.decorator import lambda_handler, response
from shared.singleton import DynamoDBClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Singleton: DynamoDB client (reused across warm invocations)
# ---------------------------------------------------------------------------
db = DynamoDBClient()
table = db.table("lab-ms-notifications")

TABLE_NAME = "lab-ms-notifications"
RECIPIENT_INDEX = "recipient-index"


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------
@lambda_handler()
def handler(event, context):
    """
    Main entry point. API Gateway proxy integration routes requests here.
    """
    http_method = event.get("httpMethod", "")
    path = event.get("path", "")
    path_parameters = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}

    # --- GET /api/v1/notifications/{id} ---
    if http_method == "GET" and path_parameters.get("id"):
        return _get_notification(path_parameters["id"])

    # --- GET /api/v1/notifications ---
    if http_method == "GET" and "/notifications" in path:
        return _list_notifications(query_params)

    return response(404, {"error": "Route not found"})


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------
def _get_notification(notification_id: str) -> dict:
    """Retrieve a single notification by its id."""
    result = table.get_item(Key={"id": notification_id})
    item = result.get("Item")

    if not item:
        raise KeyError(f"Notification {notification_id}")

    return response(200, item)


def _list_notifications(query_params: dict) -> dict:
    """
    List notifications with optional filtering.

    Query parameters:
      - recipient_id: filter by recipient (uses GSI)
      - skip: number of items to skip (default 0)
      - limit: max items to return (default 20, max 100)
    """
    recipient_id = query_params.get("recipient_id")
    skip = int(query_params.get("skip", 0))
    limit = min(int(query_params.get("limit", 20)), 100)

    if recipient_id:
        items = _query_by_recipient(recipient_id)
    else:
        items = _scan_all()

    # Sort by created_at descending (newest first)
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    total = len(items)
    paginated = items[skip : skip + limit]

    return response(200, {
        "data": paginated,
        "total": total,
        "skip": skip,
        "limit": limit,
    })


def _query_by_recipient(recipient_id: str) -> list:
    """Query notifications for a specific recipient using the GSI."""
    from boto3.dynamodb.conditions import Key

    result = table.query(
        IndexName=RECIPIENT_INDEX,
        KeyConditionExpression=Key("recipient_id").eq(recipient_id),
        ScanIndexForward=False,  # newest first
    )
    return result.get("Items", [])


def _scan_all() -> list:
    """Scan the entire table (suitable for lab/small datasets)."""
    items = []
    params = {}

    while True:
        result = table.scan(**params)
        items.extend(result.get("Items", []))

        last_key = result.get("LastEvaluatedKey")
        if not last_key:
            break
        params["ExclusiveStartKey"] = last_key

    return items
