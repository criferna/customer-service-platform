"""
=============================================================================
CAPA DE INFRAESTRUCTURA - Conexión a Base de Datos
=============================================================================
Gestiona la conexión asíncrona a PostgreSQL usando SQLAlchemy.

PATRÓN: Database per Service
  Este módulo conecta SOLO a la BD de customers (cs_customers).
  La URL de conexión viene por variable de entorno, inyectada por Docker Compose.
  Cada microservicio tiene su propia BD — no hay acceso cruzado.

Usamos conexión asíncrona (asyncpg) para no bloquear el event loop de FastAPI.
=============================================================================
"""

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Leer URL de conexión desde variable de entorno (inyectada por Docker Compose).
# Formato: postgresql://user:pass@host:port/dbname
# Se reemplaza 'postgresql://' por 'postgresql+asyncpg://' para usar el driver asíncrono.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/cs_customers")
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Engine asíncrono con pool de conexiones.
# pool_size=5: mantiene 5 conexiones abiertas (suficiente para el lab).
# echo=False: no loguear cada query SQL (cambiar a True para debug).
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    echo=False,
)

# Session factory: crea sesiones de BD para cada request.
# expire_on_commit=False: evita recargar objetos después de commit.
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """
    Dependency injection para FastAPI.
    Crea una sesión de BD por request y la cierra al terminar.
    """
    async with AsyncSessionLocal() as session:
        yield session
