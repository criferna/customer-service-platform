"""
=============================================================================
CAPA DE INFRAESTRUCTURA - Repositorio de Clientes
=============================================================================
El Repositorio es un patrón DDD que abstrae el acceso a datos.
La capa de Aplicación usa el Repositorio sin saber si los datos
vienen de PostgreSQL, MongoDB, un cache, o una API externa.

PRINCIPIO: Inversión de Dependencias (DIP)
  Los Use Cases dependen de la abstracción (Repository),
  no del detalle concreto (SQLAlchemy, PostgreSQL).

PATRÓN: Repository
  - Encapsula toda la lógica de acceso a datos
  - Convierte entre modelo de BD y entidad de dominio
  - Maneja queries, filtros y paginación
=============================================================================
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.customer import Customer
from src.infrastructure.database.models import CustomerModel

logger = logging.getLogger(__name__)


class CustomerRepository:
    """
    Repositorio para la entidad Customer.
    Traduce entre el modelo de dominio y el modelo de persistencia.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_entity(self, model: CustomerModel) -> Customer:
        """Convierte modelo de BD a entidad de dominio."""
        return Customer(
            id=model.id,
            first_name=model.first_name,
            last_name=model.last_name,
            email=model.email,
            phone=model.phone,
            company=model.company,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: Customer) -> CustomerModel:
        """Convierte entidad de dominio a modelo de BD."""
        return CustomerModel(
            id=entity.id,
            first_name=entity.first_name,
            last_name=entity.last_name,
            email=entity.email,
            phone=entity.phone,
            company=entity.company,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    async def create(self, customer: Customer) -> Customer:
        """Persiste un nuevo cliente en la BD."""
        model = self._to_model(customer)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, customer_id: UUID) -> Optional[Customer]:
        """Obtiene un cliente por su ID."""
        result = await self._session.get(CustomerModel, customer_id)
        return self._to_entity(result) if result else None

    async def list_all(self, skip: int = 0, limit: int = 20) -> list[Customer]:
        """Lista clientes activos (no eliminados) con paginación."""
        query = (
            select(CustomerModel)
            .where(CustomerModel.deleted_at.is_(None))
            .order_by(CustomerModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(query)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def update(self, customer: Customer) -> Customer:
        """Actualiza un cliente existente."""
        model = await self._session.get(CustomerModel, customer.id)
        if model:
            model.first_name = customer.first_name
            model.last_name = customer.last_name
            model.email = customer.email
            model.phone = customer.phone
            model.company = customer.company
            model.updated_at = customer.updated_at
            model.deleted_at = customer.deleted_at
            await self._session.commit()
            await self._session.refresh(model)
            return self._to_entity(model)
        raise ValueError(f"Customer {customer.id} not found")
