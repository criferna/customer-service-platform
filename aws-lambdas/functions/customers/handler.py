# =============================================================================
# BOUNDED CONTEXT: CUSTOMERS (Contexto Delimitado: Clientes)
# =============================================================================
# En Domain-Driven Design (DDD), un Bounded Context es un límite explícito
# dentro del cual un modelo de dominio particular es definido y aplicable.
#
# Este microservicio encapsula TODO lo relacionado con la gestión de clientes:
#   - Aggregate Root: Customer (entidad principal con identidad única)
#   - Value Objects: email, phone (inmutables, definidos por su valor)
#   - Repository: DynamoDB table "lab-ms-customers" (persistencia del aggregate)
#   - Domain Events: customer.created, customer.updated, customer.deleted
#
# PRINCIPIOS APLICADOS:
#   - Single Responsibility: solo gestiona clientes, nada más
#   - Soft Delete: los clientes nunca se eliminan físicamente (deleted_at)
#   - Event-Driven: cada mutación publica un evento de dominio via SNS
#   - Ubiquitous Language: los nombres reflejan el lenguaje del negocio
#
# COMUNICACIÓN CON OTROS BOUNDED CONTEXTS:
#   Este servicio NO llama directamente a otros servicios.
#   En cambio, publica Domain Events que otros contextos consumen:
#     - Tickets Context: escucha customer.created para permitir crear tickets
#     - Notifications Context: escucha customer.updated para actualizar datos
#     - Agents Context: puede consultar clientes via API si lo necesita
#
# La independencia entre contextos se logra mediante:
#   1. Cada contexto tiene su propia base de datos (Database per Service)
#   2. La comunicación es asíncrona via eventos (SNS → SQS)
#   3. Cada contexto puede evolucionar independientemente
# =============================================================================

import os
import time
import uuid

from shared.decorator import lambda_handler, response
from shared.singleton import DynamoDBClient
from shared.observer import DomainEventPublisher

# ---------------------------------------------------------------------------
# Inicialización (se ejecuta UNA VEZ por contenedor Lambda - warm start)
# ---------------------------------------------------------------------------
TABLE_NAME = "lab-ms-customers"
SERVICE_NAME = os.environ.get("SERVICE_NAME", "customers-service")

db = DynamoDBClient()
table = db.table(TABLE_NAME)
publisher = DomainEventPublisher(service_name=SERVICE_NAME)


# ---------------------------------------------------------------------------
# Handler principal con decoradores aplicados
# ---------------------------------------------------------------------------
@lambda_handler()
def handler(event, context):
    """
    Router principal del servicio de Clientes.

    API Gateway envía el evento con httpMethod y path.
    Internamente se rutea según el método HTTP y la presencia de {id}
    en pathParameters.

    Rutas soportadas:
        GET    /api/v1/customers       → list_customers
        POST   /api/v1/customers       → create_customer
        GET    /api/v1/customers/{id}  → get_customer
        PUT    /api/v1/customers/{id}  → update_customer
        DELETE /api/v1/customers/{id}  → delete_customer (soft delete)
    """
    http_method = event.get("httpMethod", "")
    path_params = event.get("pathParameters") or {}
    customer_id = path_params.get("id")

    # Ruteo interno basado en método HTTP y presencia de ID
    if customer_id:
        if http_method == "GET":
            return get_customer(customer_id)
        elif http_method == "PUT":
            return update_customer(customer_id, event)
        elif http_method == "DELETE":
            return delete_customer(customer_id, event)
        else:
            return response(405, {"error": f"Method {http_method} not allowed"})
    else:
        if http_method == "GET":
            return list_customers(event)
        elif http_method == "POST":
            return create_customer(event)
        else:
            return response(405, {"error": f"Method {http_method} not allowed"})


# ---------------------------------------------------------------------------
# Operaciones del Aggregate Root: Customer
# ---------------------------------------------------------------------------

def list_customers(event):
    """
    Lista clientes activos (no eliminados) con paginación skip/limit.

    Usa scan con FilterExpression para excluir soft-deleted.
    En producción con alta cardinalidad, se recomendaría un GSI
    con partition key por estado o usar paginación basada en cursor.
    """
    query_params = event.get("queryStringParameters") or {}
    skip = int(query_params.get("skip", 0))
    limit = int(query_params.get("limit", 20))

    # Scan con filtro: solo clientes NO eliminados
    scan_kwargs = {
        "FilterExpression": "attribute_not_exists(deleted_at) OR deleted_at = :null",
        "ExpressionAttributeValues": {":null": None},
    }

    items = []
    last_evaluated_key = None

    # DynamoDB scan es paginado internamente; recopilamos hasta tener suficientes
    while True:
        if last_evaluated_key:
            scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

        result = table.scan(**scan_kwargs)
        items.extend(result.get("Items", []))
        last_evaluated_key = result.get("LastEvaluatedKey")

        # Si ya tenemos suficientes registros o no hay más páginas, salimos
        if not last_evaluated_key or len(items) >= skip + limit:
            break

    # Aplicar skip/limit sobre los resultados recopilados
    paginated = items[skip : skip + limit]

    return response(200, {
        "data": paginated,
        "pagination": {
            "skip": skip,
            "limit": limit,
            "total": len(items),
        },
    })


def create_customer(event):
    """
    Crea un nuevo cliente (Customer Aggregate).

    Validaciones:
      - Campos requeridos: first_name, last_name, email
      - Email único (consultado via GSI email-index)

    Tras la creación, publica evento customer.created para que
    otros Bounded Contexts reaccionen (ej: Tickets permite crear tickets
    para este cliente).
    """
    body = event.get("parsed_body", {})
    correlation_id = event.get("correlation_id", "")

    # Validar campos requeridos del Aggregate
    required_fields = ["first_name", "last_name", "email"]
    missing = [f for f in required_fields if not body.get(f)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    # Verificar unicidad de email via GSI
    email = body["email"].strip().lower()
    existing = table.query(
        IndexName="email-index",
        KeyConditionExpression="email = :email",
        ExpressionAttributeValues={":email": email},
    )
    if existing.get("Items"):
        raise ValueError(f"A customer with email '{email}' already exists")

    # Construir el Aggregate Root
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    customer = {
        "id": str(uuid.uuid4()),
        "first_name": body["first_name"].strip(),
        "last_name": body["last_name"].strip(),
        "email": email,
        "phone": body.get("phone", "").strip(),
        "company": body.get("company", "").strip(),
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }

    # Persistir en el Repository (DynamoDB)
    table.put_item(Item=customer)

    # Publicar Domain Event: customer.created
    publisher.publish(
        event_type="customer.created",
        aggregate_id=customer["id"],
        payload=customer,
        correlation_id=correlation_id,
    )

    return response(201, {"data": customer})


def get_customer(customer_id):
    """
    Obtiene un cliente por su ID (identidad del Aggregate Root).

    Retorna 404 si no existe o fue soft-deleted.
    """
    result = table.get_item(Key={"id": customer_id})
    customer = result.get("Item")

    if not customer or customer.get("deleted_at"):
        raise KeyError(f"Customer {customer_id}")

    return response(200, {"data": customer})


def update_customer(customer_id, event):
    """
    Actualiza un cliente existente.

    Solo actualiza los campos proporcionados en el body (partial update).
    No permite modificar id, created_at ni deleted_at directamente.
    Publica evento customer.updated tras la modificación.
    """
    body = event.get("parsed_body", {})
    correlation_id = event.get("correlation_id", "")

    # Verificar que el customer existe y no está eliminado
    result = table.get_item(Key={"id": customer_id})
    customer = result.get("Item")

    if not customer or customer.get("deleted_at"):
        raise KeyError(f"Customer {customer_id}")

    # Campos permitidos para actualización
    updatable_fields = ["first_name", "last_name", "email", "phone", "company"]
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Construir expresión de actualización dinámica
    update_parts = []
    expression_values = {}
    expression_names = {}

    for field in updatable_fields:
        if field in body:
            value = body[field].strip() if isinstance(body[field], str) else body[field]
            # Si actualizan email, normalizar a minúsculas
            if field == "email":
                value = value.lower()
            placeholder = f":val_{field}"
            name_placeholder = f"#attr_{field}"
            update_parts.append(f"{name_placeholder} = {placeholder}")
            expression_values[placeholder] = value
            expression_names[name_placeholder] = field

    if not update_parts:
        raise ValueError("No valid fields provided for update")

    # Siempre actualizar updated_at
    update_parts.append("#attr_updated_at = :val_updated_at")
    expression_values[":val_updated_at"] = now
    expression_names["#attr_updated_at"] = "updated_at"

    update_expression = "SET " + ", ".join(update_parts)

    updated = table.update_item(
        Key={"id": customer_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_values,
        ExpressionAttributeNames=expression_names,
        ReturnValues="ALL_NEW",
    )

    updated_customer = updated.get("Attributes", {})

    # Publicar Domain Event: customer.updated
    publisher.publish(
        event_type="customer.updated",
        aggregate_id=customer_id,
        payload=updated_customer,
        correlation_id=correlation_id,
    )

    return response(200, {"data": updated_customer})


def delete_customer(customer_id, event):
    """
    Soft delete de un cliente.

    En DDD, la eliminación lógica preserva la historia del Aggregate.
    Se marca deleted_at con el timestamp actual en lugar de eliminar
    físicamente el registro. Esto permite:
      - Auditoría completa del ciclo de vida del cliente
      - Restauración si fue un error
      - Integridad referencial con tickets existentes

    Publica evento customer.deleted para que otros contextos reaccionen
    (ej: Tickets podría marcar tickets huérfanos).
    """
    correlation_id = event.get("correlation_id", "")

    # Verificar que existe y no está ya eliminado
    result = table.get_item(Key={"id": customer_id})
    customer = result.get("Item")

    if not customer or customer.get("deleted_at"):
        raise KeyError(f"Customer {customer_id}")

    # Marcar como eliminado (soft delete)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    table.update_item(
        Key={"id": customer_id},
        UpdateExpression="SET deleted_at = :deleted_at, updated_at = :updated_at",
        ExpressionAttributeValues={
            ":deleted_at": now,
            ":updated_at": now,
        },
    )

    # Publicar Domain Event: customer.deleted
    publisher.publish(
        event_type="customer.deleted",
        aggregate_id=customer_id,
        payload={"id": customer_id, "deleted_at": now},
        correlation_id=correlation_id,
    )

    return response(200, {
        "message": f"Customer {customer_id} deleted successfully",
        "deleted_at": now,
    })
