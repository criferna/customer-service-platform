"""
=============================================================================
CAPA DE APLICACIÓN - Data Transfer Objects (DTOs)
=============================================================================
Los DTOs definen la forma de los datos que entran y salen del servicio.
Actúan como contratos de la API (Autonomía - Slide 17: "Contratos bien establecidos").

Usamos Pydantic para:
  - Validación automática de datos de entrada
  - Serialización/deserialización JSON
  - Documentación automática en Swagger/OpenAPI
=============================================================================
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CreateCustomerDTO(BaseModel):
    """DTO para crear un nuevo cliente. Valida datos de entrada."""
    first_name: str = Field(..., min_length=1, max_length=100, examples=["María"])
    last_name: str = Field(..., min_length=1, max_length=100, examples=["González"])
    email: str = Field(..., max_length=255, examples=["maria@example.com"])
    phone: Optional[str] = Field(None, max_length=50, examples=["+56912345678"])
    company: Optional[str] = Field(None, max_length=200, examples=["TechCorp"])


class UpdateCustomerDTO(BaseModel):
    """DTO para actualizar un cliente. Todos los campos son opcionales."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    company: Optional[str] = Field(None, max_length=200)


class CustomerResponseDTO(BaseModel):
    """DTO de respuesta. Define el contrato público del servicio."""
    id: UUID
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
