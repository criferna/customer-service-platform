"""
=============================================================================
CAPA DE DOMINIO - Entidad Customer
=============================================================================
En DDD, una Entidad es un objeto que tiene identidad propia (UUID).
Dos entidades con los mismos atributos pero diferente ID son DISTINTAS.

La entidad Customer representa el concepto de negocio "Cliente" dentro
del Bounded Context de Gestión de Clientes. Contiene:

  - Atributos del dominio (nombre, email, teléfono, empresa)
  - Reglas de negocio (validaciones)
  - Métodos de dominio (update, soft_delete)

PRINCIPIO DDD: La entidad NO conoce la base de datos ni la infraestructura.
Es puro dominio de negocio. La persistencia la maneja la capa de Infraestructura.

REFERENCIA: Slide 25 - "Entidades, Objetos de Valor, Servicios"
=============================================================================
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class Customer:
    """
    Entidad Customer - Bounded Context: Gestión de Clientes.

    Representa un cliente de la plataforma de servicio al cliente.
    Tiene identidad propia (id) y ciclo de vida completo.
    """

    # Identidad: UUID generado al crear. Dos Customer con mismo nombre
    # pero diferente id son entidades distintas (principio de identidad DDD).
    id: UUID = field(default_factory=uuid4)

    # Atributos del dominio (Ubiquitous Language)
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: Optional[str] = None
    company: Optional[str] = None

    # Ciclo de vida
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None

    @property
    def full_name(self) -> str:
        """Nombre completo del cliente (Ubiquitous Language)."""
        return f"{self.first_name} {self.last_name}"

    @property
    def is_deleted(self) -> bool:
        """Indica si el cliente fue eliminado (soft delete)."""
        return self.deleted_at is not None

    def update(self, **kwargs) -> list[str]:
        """
        Actualiza los atributos del cliente.
        Retorna la lista de campos que cambiaron (útil para eventos).

        Regla de negocio: solo se actualizan campos permitidos.
        """
        allowed = {"first_name", "last_name", "email", "phone", "company"}
        changed = []

        for key, value in kwargs.items():
            if key in allowed and getattr(self, key) != value:
                setattr(self, key, value)
                changed.append(key)

        if changed:
            self.updated_at = datetime.utcnow()

        return changed

    def soft_delete(self) -> None:
        """
        Soft delete: marca al cliente como eliminado sin borrarlo de la BD.

        En microservicios, NO se hacen hard deletes porque otros servicios
        pueden tener copias locales de datos del cliente (desnormalización).
        El evento 'customer.deleted' notifica a los otros servicios.
        """
        self.deleted_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
