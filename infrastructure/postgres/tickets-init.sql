-- =============================================================================
-- Tickets Service - Database Schema (IaC)
-- =============================================================================
-- Bounded Context: Gestión de Tickets / Incidencias
--
-- ENTIDAD: Ticket
--   - Ciclo de vida con workflow de estados (State Machine Pattern)
--   - Contiene datos desnormalizados de Customer y Agent (copias locales)
--
-- PATRÓN: Datos Desnormalizados
--   customer_name, customer_email, assigned_agent_name se almacenan localmente.
--   NO se hace JOIN a otros servicios. Se actualizan vía eventos.
--   Si customers-service está caído, tickets-service sigue funcionando
--   con los datos que tiene (Autonomía - Slide 17).
--
-- PATRÓN: Saga Coreografiada
--   La creación de un ticket dispara una cadena de eventos:
--   ticket.created → agents-service reserva agente → ticket.assigned
--   Si no hay agente disponible, el ticket queda como UNASSIGNED.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tipo enumerado para estados del ticket (State Machine)
-- Workflow: OPEN → ASSIGNED → IN_PROGRESS → RESOLVED → CLOSED
--                                          → REOPENED → ASSIGNED
CREATE TYPE ticket_status AS ENUM (
    'OPEN',         -- Recién creado, sin agente asignado
    'ASSIGNED',     -- Agente asignado, esperando que comience
    'IN_PROGRESS',  -- Agente trabajando en el ticket
    'RESOLVED',     -- Agente resolvió el problema
    'CLOSED',       -- Cliente confirmó resolución o timeout
    'REOPENED'      -- Cliente reporta que el problema persiste
);

-- Prioridad del ticket
CREATE TYPE ticket_priority AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'URGENT');

-- Tabla principal de tickets
CREATE TABLE IF NOT EXISTS tickets (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Datos propios del ticket (Bounded Context)
    subject             VARCHAR(300) NOT NULL,
    description         TEXT NOT NULL,
    status              ticket_status NOT NULL DEFAULT 'OPEN',
    priority            ticket_priority NOT NULL DEFAULT 'MEDIUM',

    -- Datos DESNORMALIZADOS del cliente (copia local).
    -- Se actualizan cuando llega un evento 'customer.updated' de RabbitMQ.
    -- Esto permite que tickets-service funcione aunque customers-service esté caído.
    customer_id         UUID NOT NULL,
    customer_name       VARCHAR(200) NOT NULL,
    customer_email      VARCHAR(255) NOT NULL,

    -- Datos DESNORMALIZADOS del agente asignado (copia local).
    -- Se actualizan cuando llega un evento 'agent.updated' de RabbitMQ.
    assigned_agent_id   UUID,
    assigned_agent_name VARCHAR(200),

    -- Auditoría y timestamps del workflow
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    assigned_at         TIMESTAMP WITH TIME ZONE,
    resolved_at         TIMESTAMP WITH TIME ZONE,
    closed_at           TIMESTAMP WITH TIME ZONE
);

-- Índices optimizados para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_customer ON tickets(customer_id);
CREATE INDEX IF NOT EXISTS idx_tickets_agent ON tickets(assigned_agent_id);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority, status);
CREATE INDEX IF NOT EXISTS idx_tickets_created ON tickets(created_at DESC);

-- Transactional Outbox para publicación atómica de eventos
CREATE TABLE IF NOT EXISTS outbox_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aggregate_type  VARCHAR(100) NOT NULL,
    aggregate_id    UUID NOT NULL,
    event_type      VARCHAR(100) NOT NULL,
    payload         JSONB NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    published_at    TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_outbox_unpublished ON outbox_events(created_at)
    WHERE published_at IS NULL;

-- Datos de ejemplo
INSERT INTO tickets (id, subject, description, status, priority, customer_id, customer_name, customer_email) VALUES
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'No puedo acceder a mi cuenta', 'Intento hacer login pero me da error 403', 'OPEN', 'HIGH',
     'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'María González', 'maria.gonzalez@example.com'),
    ('e0eebc99-9c0b-4ef8-bb6d-6bb9bd380a55', 'Error en facturación', 'Me cobraron dos veces el mes pasado', 'OPEN', 'URGENT',
     'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'Carlos Rodríguez', 'carlos.rodriguez@example.com')
ON CONFLICT (id) DO NOTHING;
