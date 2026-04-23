# =============================================================================
# BOUNDED CONTEXT: KNOWLEDGE BASE (Contexto Delimitado: Base de Conocimiento)
# =============================================================================
# En Domain-Driven Design (DDD), este Bounded Context encapsula la gestión
# del conocimiento interno del equipo de soporte: categorías y artículos.
#
# AGGREGATES:
#   - Category: clasificación temática de artículos
#   - Article: contenido de conocimiento asociado a una categoría
#
# RELACIÓN ENTRE AGGREGATES:
#   Article referencia a Category via category_id (referencia por identidad).
#   Cada Aggregate tiene su propia tabla DynamoDB (una tabla por Aggregate),
#   lo que permite escalar y evolucionar independientemente.
#
# INDEPENDENCIA TECNOLÓGICA:
#   Este es un ejemplo clave del principio de independencia tecnológica en
#   microservicios. El mismo Bounded Context se implementa:
#     - En Docker: con Go + Gin (servicio knowledge-service)
#     - En AWS: con Python 3.12 + Lambda (este handler)
#
#   Ambas implementaciones exponen la misma API REST y manejan los mismos
#   datos, demostrando que la tecnología es un detalle de implementación,
#   NO una decisión arquitectónica del dominio.
#
# DOMAIN EVENTS:
#   - article.created, article.updated
#   - category.created
#   Otros Bounded Contexts pueden escuchar estos eventos para, por ejemplo,
#   sugerir artículos relevantes al resolver tickets.
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
CATEGORIES_TABLE = "lab-ms-knowledge-categories"
ARTICLES_TABLE = "lab-ms-knowledge-articles"
SERVICE_NAME = os.environ.get("SERVICE_NAME", "knowledge-service")

db = DynamoDBClient()
categories_table = db.table(CATEGORIES_TABLE)
articles_table = db.table(ARTICLES_TABLE)
publisher = DomainEventPublisher(service_name=SERVICE_NAME)


# ---------------------------------------------------------------------------
# Handler principal con decoradores aplicados
# ---------------------------------------------------------------------------
@lambda_handler()
def handler(event, context):
    """
    Router principal del servicio de Knowledge Base.

    Rutea según el path (categories vs articles) y el método HTTP.
    Soporta dos sub-recursos bajo /api/v1/:
      - /categories → gestión de categorías
      - /articles   → gestión de artículos

    Rutas soportadas:
        GET    /api/v1/categories       → list_categories
        POST   /api/v1/categories       → create_category
        GET    /api/v1/articles          → list_articles (filtro por category_id)
        POST   /api/v1/articles          → create_article
        GET    /api/v1/articles/{id}     → get_article
        PUT    /api/v1/articles/{id}     → update_article
    """
    http_method = event.get("httpMethod", "")
    path = event.get("path", "")
    path_params = event.get("pathParameters") or {}
    resource_id = path_params.get("id")

    # Determinar si la ruta es para categorías o artículos
    if "/categories" in path:
        return _route_categories(http_method, resource_id, event)
    elif "/articles" in path:
        return _route_articles(http_method, resource_id, event)
    else:
        return response(404, {"error": f"Route not found: {path}"})


# ---------------------------------------------------------------------------
# Router de sub-recursos
# ---------------------------------------------------------------------------

def _route_categories(http_method, resource_id, event):
    """Ruteo interno para el Aggregate Category."""
    if resource_id:
        if http_method == "GET":
            return get_category(resource_id)
        else:
            return response(405, {"error": f"Method {http_method} not allowed for categories/{{id}}"})
    else:
        if http_method == "GET":
            return list_categories()
        elif http_method == "POST":
            return create_category(event)
        else:
            return response(405, {"error": f"Method {http_method} not allowed for categories"})


def _route_articles(http_method, resource_id, event):
    """Ruteo interno para el Aggregate Article."""
    if resource_id:
        if http_method == "GET":
            return get_article(resource_id)
        elif http_method == "PUT":
            return update_article(resource_id, event)
        else:
            return response(405, {"error": f"Method {http_method} not allowed for articles/{{id}}"})
    else:
        if http_method == "GET":
            return list_articles(event)
        elif http_method == "POST":
            return create_article(event)
        else:
            return response(405, {"error": f"Method {http_method} not allowed for articles"})


# ---------------------------------------------------------------------------
# Operaciones del Aggregate: Category
# ---------------------------------------------------------------------------

def list_categories():
    """
    Lista todas las categorías de conocimiento.

    Las categorías son un Aggregate simple sin soft-delete:
    se asume que son pocas y administradas internamente.
    """
    result = categories_table.scan()
    items = result.get("Items", [])

    # Manejar paginación de DynamoDB si hay muchos registros
    while result.get("LastEvaluatedKey"):
        result = categories_table.scan(
            ExclusiveStartKey=result["LastEvaluatedKey"]
        )
        items.extend(result.get("Items", []))

    return response(200, {"data": items})


def create_category(event):
    """
    Crea una nueva categoría de conocimiento.

    Campos requeridos: name
    Publica evento category.created.
    """
    body = event.get("parsed_body", {})
    correlation_id = event.get("correlation_id", "")

    if not body.get("name"):
        raise ValueError("Missing required field: name")

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    category = {
        "id": str(uuid.uuid4()),
        "name": body["name"].strip(),
        "description": body.get("description", "").strip(),
        "created_at": now,
        "updated_at": now,
    }

    categories_table.put_item(Item=category)

    publisher.publish(
        event_type="category.created",
        aggregate_id=category["id"],
        payload=category,
        correlation_id=correlation_id,
    )

    return response(201, {"data": category})


def get_category(category_id):
    """Obtiene una categoría por ID."""
    result = categories_table.get_item(Key={"id": category_id})
    category = result.get("Item")

    if not category:
        raise KeyError(f"Category {category_id}")

    return response(200, {"data": category})


# ---------------------------------------------------------------------------
# Operaciones del Aggregate: Article
# ---------------------------------------------------------------------------

def list_articles(event):
    """
    Lista artículos de conocimiento.

    Soporta filtro por category_id via queryStringParameters.
    Si se proporciona category_id, usa el GSI category-index para
    una consulta eficiente en lugar de un scan completo.
    """
    query_params = event.get("queryStringParameters") or {}
    category_id = query_params.get("category_id")

    if category_id:
        # Consulta eficiente via GSI category-index
        result = articles_table.query(
            IndexName="category-index",
            KeyConditionExpression="category_id = :cid",
            ExpressionAttributeValues={":cid": category_id},
        )
        items = result.get("Items", [])

        while result.get("LastEvaluatedKey"):
            result = articles_table.query(
                IndexName="category-index",
                KeyConditionExpression="category_id = :cid",
                ExpressionAttributeValues={":cid": category_id},
                ExclusiveStartKey=result["LastEvaluatedKey"],
            )
            items.extend(result.get("Items", []))
    else:
        # Sin filtro: scan completo
        result = articles_table.scan()
        items = result.get("Items", [])

        while result.get("LastEvaluatedKey"):
            result = articles_table.scan(
                ExclusiveStartKey=result["LastEvaluatedKey"]
            )
            items.extend(result.get("Items", []))

    return response(200, {"data": items, "count": len(items)})


def create_article(event):
    """
    Crea un nuevo artículo de conocimiento.

    Campos requeridos: title, content, category_id
    El artículo se crea como no publicado (published=False) por defecto.

    Valida que la categoría referenciada exista (integridad referencial
    a nivel de aplicación, ya que DynamoDB no soporta foreign keys).
    """
    body = event.get("parsed_body", {})
    correlation_id = event.get("correlation_id", "")

    # Validar campos requeridos
    required_fields = ["title", "content", "category_id"]
    missing = [f for f in required_fields if not body.get(f)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    # Validar que la categoría existe (integridad referencial por aplicación)
    cat_result = categories_table.get_item(Key={"id": body["category_id"]})
    if not cat_result.get("Item"):
        raise ValueError(f"Category '{body['category_id']}' does not exist")

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    article = {
        "id": str(uuid.uuid4()),
        "title": body["title"].strip(),
        "content": body["content"].strip(),
        "category_id": body["category_id"],
        "author_agent_id": body.get("author_agent_id", ""),
        "author_agent_name": body.get("author_agent_name", ""),
        "tags": body.get("tags", []),
        "published": body.get("published", False),
        "created_at": now,
        "updated_at": now,
    }

    articles_table.put_item(Item=article)

    publisher.publish(
        event_type="article.created",
        aggregate_id=article["id"],
        payload=article,
        correlation_id=correlation_id,
    )

    return response(201, {"data": article})


def get_article(article_id):
    """Obtiene un artículo por su ID."""
    result = articles_table.get_item(Key={"id": article_id})
    article = result.get("Item")

    if not article:
        raise KeyError(f"Article {article_id}")

    return response(200, {"data": article})


def update_article(article_id, event):
    """
    Actualiza un artículo existente.

    Permite actualización parcial de cualquier campo excepto id y created_at.
    Publica evento article.updated tras la modificación.
    """
    body = event.get("parsed_body", {})
    correlation_id = event.get("correlation_id", "")

    # Verificar que el artículo existe
    result = articles_table.get_item(Key={"id": article_id})
    article = result.get("Item")

    if not article:
        raise KeyError(f"Article {article_id}")

    # Si actualizan category_id, validar que la nueva categoría existe
    if "category_id" in body:
        cat_result = categories_table.get_item(Key={"id": body["category_id"]})
        if not cat_result.get("Item"):
            raise ValueError(f"Category '{body['category_id']}' does not exist")

    # Campos permitidos para actualización
    updatable_fields = [
        "title", "content", "category_id", "author_agent_id",
        "author_agent_name", "tags", "published",
    ]
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Construir expresión de actualización dinámica
    update_parts = []
    expression_values = {}
    expression_names = {}

    for field in updatable_fields:
        if field in body:
            value = body[field]
            if isinstance(value, str):
                value = value.strip()
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

    updated = articles_table.update_item(
        Key={"id": article_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_values,
        ExpressionAttributeNames=expression_names,
        ReturnValues="ALL_NEW",
    )

    updated_article = updated.get("Attributes", {})

    publisher.publish(
        event_type="article.updated",
        aggregate_id=article_id,
        payload=updated_article,
        correlation_id=correlation_id,
    )

    return response(200, {"data": updated_article})
