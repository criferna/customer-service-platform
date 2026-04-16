-- =============================================================================
-- Customers Service - Database Schema (IaC)
-- =============================================================================
-- Bounded Context: Gestión de Clientes
--
-- Este script se ejecuta automáticamente al crear el contenedor PostgreSQL.
-- Define el schema del servicio de clientes siguiendo principios DDD:
--
--   ENTIDAD: Customer
--     - Tiene identidad propia (UUID)
--     - Ciclo de vida completo (created_at, updated_at, deleted_at)
--     - Soft delete para mantener integridad referencial con otros servicios
--
--   VALUE OBJECTS (representados como columnas):
--     - Email: validado como único, identifica al cliente
--     - Phone: formato libre para flexibilidad internacional
--
-- PATRÓN: Database per Service
--   Esta BD es EXCLUSIVA del customers-service.
--   Ningún otro servicio puede acceder a ella directamente.
--   Otros servicios obtienen datos de clientes vía API o eventos.
-- =============================================================================

-- Extensión para generar UUIDs v4 (identificadores únicos universales)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabla principal de clientes
CREATE TABLE IF NOT EXISTS customers (
    -- Identificador único universal. Preferido sobre auto-increment porque:
    -- 1. No revela información sobre el volumen de datos
    -- 2. Se puede generar en el cliente sin consultar la BD
    -- 3. Es único globalmente (útil en sistemas distribuidos)
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Datos del cliente (Ubiquitous Language del dominio)
    first_name  VARCHAR(100) NOT NULL,
    last_name   VARCHAR(100) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,  -- Value Object: Email
    phone       VARCHAR(50),                    -- Value Object: Phone
    company     VARCHAR(200),

    -- Auditoría y ciclo de vida
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Soft delete: no se eliminan registros, se marcan como eliminados.
    -- Esto es crítico en microservicios porque otros servicios pueden tener
    -- copias locales de datos del cliente (desnormalización).
    deleted_at  TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

-- Índices para búsquedas frecuentes
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_customers_deleted ON customers(deleted_at) WHERE deleted_at IS NULL;

-- Tabla de outbox para eventos (Transactional Outbox Pattern).
-- Garantiza que el evento se publique SOLO si la transacción de BD fue exitosa.
-- Un proceso aparte lee esta tabla y publica los eventos a RabbitMQ.
-- Esto evita el problema de "dual write" (escribir BD + publicar evento de forma atómica).
CREATE TABLE IF NOT EXISTS outbox_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aggregate_type  VARCHAR(100) NOT NULL,     -- 'Customer'
    aggregate_id    UUID NOT NULL,             -- ID del cliente afectado
    event_type      VARCHAR(100) NOT NULL,     -- 'customer.created', 'customer.updated', etc.
    payload         JSONB NOT NULL,            -- Datos del evento en JSON
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    published_at    TIMESTAMP WITH TIME ZONE DEFAULT NULL  -- NULL = pendiente de publicar
);

CREATE INDEX IF NOT EXISTS idx_outbox_unpublished ON outbox_events(created_at)
    WHERE published_at IS NULL;

-- Datos de ejemplo para el laboratorio
INSERT INTO customers (id, first_name, last_name, email, phone, company) VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'María', 'González', 'maria.gonzalez@example.com', '+56912345678', 'TechCorp Chile'),
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'Carlos', 'Rodríguez', 'carlos.rodriguez@example.com', '+56987654321', 'Innovatech'),
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'Ana', 'Martínez', 'ana.martinez@example.com', '+56911223344', NULL)
ON CONFLICT (email) DO NOTHING;
