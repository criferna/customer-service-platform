"""
=============================================================================
CAPA DE INFRAESTRUCTURA - Modelo SQLAlchemy (ORM)
=============================================================================
Mapea la entidad de dominio Customer a la tabla de la BD.

PRINCIPIO DDD: El modelo de BD es un detalle de INFRAESTRUCTURA.
  La entidad de dominio (domain/entities/customer.py) no sabe de SQLAlchemy.
  Este modelo es el puente entre el dominio y la persistencia.
  Si mañana cambiamos de PostgreSQL a MongoDB, solo cambia esta capa.
=============================================================================
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Clase base para todos los modelos SQLAlchemy."""
    pass


class CustomerModel(Base):
    """Modelo de persistencia para la entidad Customer."""

    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
