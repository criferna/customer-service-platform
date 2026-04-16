"""
=============================================================================
CAPA DE APLICACIÓN - Casos de Uso (Use Cases / Application Services)
=============================================================================
Los Casos de Uso orquestan la lógica de la aplicación:
  1. Reciben datos del mundo exterior (DTOs)
  2. Interactúan con el Dominio (entidades, reglas de negocio)
  3. Usan la Infraestructura (repositorio, messaging)
  4. Retornan resultados

PRINCIPIO DDD: Los Use Cases NO contienen lógica de negocio.
Esa lógica vive en las entidades del Dominio.
Los Use Cases solo COORDINAN el flujo.

REFERENCIA: Slide 25 - Capa de Aplicación
  La capa de Aplicación es el pegamento entre la Presentación y el Dominio.
  Coordina las acciones pero delega la lógica a las entidades.
=============================================================================
"""

import logging
from typing import Optional
from uuid import UUID

from src.application.dto.customer_dto import (
    CreateCustomerDTO,
    CustomerResponseDTO,
    UpdateCustomerDTO,
)
from src.domain.entities.customer import Customer
from src.domain.events.customer_events import (
    CustomerCreated,
    CustomerDeleted,
    CustomerUpdated,
)
from src.infrastructure.messaging.event_publisher import EventPublisher
from src.infrastructure.repositories.customer_repository import CustomerRepository

logger = logging.getLogger(__name__)


class CustomerUseCases:
    """
    Casos de Uso del Bounded Context de Clientes.

    Cada método público representa un caso de uso del negocio.
    Usa inyección de dependencias para repositorio y publisher
    (facilita testing y respeta el principio de inversión de dependencias).
    """

    def __init__(self, repository: CustomerRepository, event_publisher: EventPublisher):
        self._repo = repository
        self._events = event_publisher

    async def create_customer(
        self, dto: CreateCustomerDTO, correlation_id: Optional[str] = None
    ) -> CustomerResponseDTO:
        """
        Caso de Uso: Crear un nuevo cliente.

        Flujo:
          1. Crear entidad Customer (dominio)
          2. Persistir en BD (infraestructura)
          3. Publicar evento customer.created (Event Bus)
          4. Retornar DTO de respuesta (presentación)
        """
        logger.info(
            "Creating customer",
            extra={"email": dto.email, "correlation_id": correlation_id},
        )

        # 1. Crear entidad de dominio
        customer = Customer(
            first_name=dto.first_name,
            last_name=dto.last_name,
            email=dto.email,
            phone=dto.phone,
            company=dto.company,
        )

        # 2. Persistir vía repositorio (capa de infraestructura)
        saved = await self._repo.create(customer)

        # 3. Publicar evento de dominio para que otros servicios se enteren.
        #    Esto implementa el patrón Event-Driven: el servicio de tickets
        #    recibirá este evento y guardará una copia local del cliente.
        event = CustomerCreated(
            aggregate_id=saved.id,
            correlation_id=correlation_id,
            payload={
                "id": str(saved.id),
                "first_name": saved.first_name,
                "last_name": saved.last_name,
                "email": saved.email,
                "phone": saved.phone,
                "company": saved.company,
            },
        )
        await self._events.publish(event)

        logger.info(
            "Customer created",
            extra={"customer_id": str(saved.id), "correlation_id": correlation_id},
        )

        # 4. Retornar DTO de respuesta
        return CustomerResponseDTO.model_validate(saved)

    async def get_customer(self, customer_id: UUID) -> Optional[CustomerResponseDTO]:
        """Caso de Uso: Obtener un cliente por ID."""
        customer = await self._repo.get_by_id(customer_id)
        if customer is None or customer.is_deleted:
            return None
        return CustomerResponseDTO.model_validate(customer)

    async def list_customers(
        self, skip: int = 0, limit: int = 20
    ) -> list[CustomerResponseDTO]:
        """Caso de Uso: Listar clientes con paginaci��n."""
        customers = await self._repo.list_all(skip=skip, limit=limit)
        return [CustomerResponseDTO.model_validate(c) for c in customers]

    async def update_customer(
        self,
        customer_id: UUID,
        dto: UpdateCustomerDTO,
        correlation_id: Optional[str] = None,
    ) -> Optional[CustomerResponseDTO]:
        """
        Caso de Uso: Actualizar datos de un cliente.

        IMPORTANTE para sincronización: al actualizar un cliente, se publica
        un evento customer.updated. Otros servicios (como tickets-service)
        que tienen copias desnormalizadas del cliente actualizarán sus datos.
        Esto es CONSISTENCIA EVENTUAL.
        """
        customer = await self._repo.get_by_id(customer_id)
        if customer is None or customer.is_deleted:
            return None

        # Usar método de dominio para actualizar (lógica en la entidad)
        update_data = dto.model_dump(exclude_unset=True)
        changed_fields = customer.update(**update_data)

        if not changed_fields:
            return CustomerResponseDTO.model_validate(customer)

        # Persistir cambios
        updated = await self._repo.update(customer)

        # Publicar evento con los campos que cambiaron.
        # Otros servicios con copias desnormalizadas actualizan solo lo necesario.
        event = CustomerUpdated(
            aggregate_id=updated.id,
            correlation_id=correlation_id,
            payload={
                "id": str(updated.id),
                "changed_fields": changed_fields,
                "first_name": updated.first_name,
                "last_name": updated.last_name,
                "email": updated.email,
                "phone": updated.phone,
                "company": updated.company,
            },
        )
        await self._events.publish(event)

        logger.info(
            "Customer updated",
            extra={
                "customer_id": str(updated.id),
                "changed": changed_fields,
                "correlation_id": correlation_id,
            },
        )

        return CustomerResponseDTO.model_validate(updated)

    async def delete_customer(
        self, customer_id: UUID, correlation_id: Optional[str] = None
    ) -> bool:
        """
        Caso de Uso: Eliminar un cliente (soft delete).

        Se usa soft delete porque otros servicios pueden tener datos
        desnormalizados de este cliente. El evento customer.deleted
        les permite actualizar su estado local.
        """
        customer = await self._repo.get_by_id(customer_id)
        if customer is None or customer.is_deleted:
            return False

        # Soft delete vía método de dominio
        customer.soft_delete()
        await self._repo.update(customer)

        # Notificar a otros servicios
        event = CustomerDeleted(
            aggregate_id=customer.id,
            correlation_id=correlation_id,
            payload={"id": str(customer.id), "email": customer.email},
        )
        await self._events.publish(event)

        logger.info(
            "Customer deleted",
            extra={"customer_id": str(customer.id), "correlation_id": correlation_id},
        )

        return True
