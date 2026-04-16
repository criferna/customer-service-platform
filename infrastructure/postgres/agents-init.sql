-- =============================================================================
-- Agents Service - Database Schema (IaC)
-- =============================================================================
-- Bounded Context: Gestión de Agentes de Soporte
--
-- ENTIDAD: Agent
--   - Agentes de soporte que atienden tickets
--   - Tiene capacidad máxima de tickets simultáneos (max_tickets)
--   - Estado de disponibilidad (ONLINE, OFFLINE, BUSY)
--   - Skills/competencias para routing inteligente de tickets
--
-- PATRÓN: Event Consumer + Producer
--   Consume: ticket.assigned (incrementa active_tickets_count)
--            ticket.resolved/closed (decrementa active_tickets_count)
--   Produce: agent.status_changed, agent.available
--
-- SINCRONIZACIÓN:
--   active_tickets_count se mantiene sincronizado vía eventos.
--   Si un ticket se asigna a este agente, el evento ticket.assigned
--   incrementa el contador. Cuando se resuelve, se decrementa.
--   Esto es consistencia eventual — puede haber un breve delay.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Estado del agente
CREATE TYPE agent_status AS ENUM ('ONLINE', 'OFFLINE', 'BUSY', 'ON_BREAK');

-- Tabla de agentes
CREATE TABLE IF NOT EXISTS agents (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Datos del agente
    first_name            VARCHAR(100) NOT NULL,
    last_name             VARCHAR(100) NOT NULL,
    email                 VARCHAR(255) NOT NULL UNIQUE,

    -- Disponibilidad y capacidad
    status                agent_status NOT NULL DEFAULT 'OFFLINE',
    max_tickets           INTEGER NOT NULL DEFAULT 5,
    active_tickets_count  INTEGER NOT NULL DEFAULT 0,

    -- Skills/competencias (array PostgreSQL para flexibilidad)
    -- Permite routing inteligente: asignar tickets de "facturación"
    -- a agentes con skill "billing"
    skills                TEXT[] DEFAULT '{}',

    -- Auditoría
    created_at            TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at            TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_agents_email ON agents(email);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_available ON agents(status, active_tickets_count)
    WHERE status = 'ONLINE';
CREATE INDEX IF NOT EXISTS idx_agents_skills ON agents USING GIN(skills);

-- Transactional Outbox
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
INSERT INTO agents (id, first_name, last_name, email, status, max_tickets, skills) VALUES
    ('10eebc99-9c0b-4ef8-bb6d-6bb9bd380a01', 'Pedro', 'López', 'pedro.lopez@support.com', 'ONLINE', 5, ARRAY['billing', 'general']),
    ('20eebc99-9c0b-4ef8-bb6d-6bb9bd380a02', 'Laura', 'Sánchez', 'laura.sanchez@support.com', 'ONLINE', 3, ARRAY['technical', 'account']),
    ('30eebc99-9c0b-4ef8-bb6d-6bb9bd380a03', 'Diego', 'Ramírez', 'diego.ramirez@support.com', 'OFFLINE', 5, ARRAY['general', 'billing', 'technical'])
ON CONFLICT (email) DO NOTHING;
