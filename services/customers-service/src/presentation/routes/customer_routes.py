"""
=============================================================================
CAPA DE PRESENTACIÓN - Rutas API REST (Customer Routes)
=============================================================================
Define los endpoints HTTP del servicio de clientes.
Esta es la "interfaz de consumo" del microservicio (Slide 10).

Contratos bien establecidos (Autonomía - Slide 17):
  - Cada endpoint tiene schema de request/response definido (DTOs)
  - Versionado en URL (/api/v1/) para evolución sin romper clientes
  - Códigos HTTP estándar (200, 201, 404, 422)
  - Documentación automática via Swagger/OpenAPI

COMUNICACIÓN: Otros servicios NO llaman a estas rutas directamente.
  Todo pasa por el API Gateway (Kong) que enruta, balancea y protege.
=============================================================================
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.customer_dto import (
    CreateCustomerDTO,
    CustomerResponseDTO,
    UpdateCustomerDTO,
)
from src.application.use_cases.customer_use_cases import CustomerUseCases
from src.infrastructure.database.connection import get_session
from src.infrastructure.messaging.event_publisher import EventPublisher
from src.infrastructure.repositories.customer_repository import CustomerRepository
from src.presentation.middleware.correlation import get_correlation_id

# Router con prefijo y tag para documentación Swagger
router = APIRouter(prefix="/api/v1/customers", tags=["Customers"])

# Instancia global del publisher (compartida entre requests)
_event_publisher = EventPublisher()


def get_use_cases(session: AsyncSession = Depends(get_session)) -> CustomerUseCases:
    """
    Dependency Injection: crea los Use Cases con sus dependencias.
    FastAPI inyecta la sesión de BD automáticamente.
    """
    repo = CustomerRepository(session)
    return CustomerUseCases(repo, _event_publisher)


@router.post(
    "",
    response_model=CustomerResponseDTO,
    status_code=201,
    summary="Crear un nuevo cliente",
    description="Crea un cliente y publica el evento customer.created al Event Bus.",
)
async def create_customer(
    dto: CreateCustomerDTO,
    use_cases: CustomerUseCases = Depends(get_use_cases),
):
    correlation_id = get_correlation_id()
    return await use_cases.create_customer(dto, correlation_id)


@router.get(
    "",
    response_model=list[CustomerResponseDTO],
    summary="Listar clientes",
    description="Lista clientes activos con paginación.",
)
async def list_customers(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(20, ge=1, le=100, description="Máximo de registros"),
    use_cases: CustomerUseCases = Depends(get_use_cases),
):
    return await use_cases.list_customers(skip=skip, limit=limit)


@router.get(
    "/{customer_id}",
    response_model=CustomerResponseDTO,
    summary="Obtener un cliente por ID",
)
async def get_customer(
    customer_id: UUID,
    use_cases: CustomerUseCases = Depends(get_use_cases),
):
    customer = await use_cases.get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put(
    "/{customer_id}",
    response_model=CustomerResponseDTO,
    summary="Actualizar un cliente",
    description="Actualiza datos del cliente y publica customer.updated. "
    "Otros servicios con datos desnormalizados se actualizarán vía eventos.",
)
async def update_customer(
    customer_id: UUID,
    dto: UpdateCustomerDTO,
    use_cases: CustomerUseCases = Depends(get_use_cases),
):
    correlation_id = get_correlation_id()
    customer = await use_cases.update_customer(customer_id, dto, correlation_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.delete(
    "/{customer_id}",
    status_code=204,
    summary="Eliminar un cliente (soft delete)",
    description="Marca al cliente como eliminado y publica customer.deleted.",
)
async def delete_customer(
    customer_id: UUID,
    use_cases: CustomerUseCases = Depends(get_use_cases),
):
    correlation_id = get_correlation_id()
    deleted = await use_cases.delete_customer(customer_id, correlation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")
