-- =============================================================================
-- Notifications Service - Database Schema (IaC)
-- =============================================================================
-- Bounded Context: Notificaciones
--
-- Este servicio es principalmente un CONSUMIDOR de eventos.
-- No expone datos a otros servicios, solo registra las notificaciones enviadas.
-- Consume eventos de RabbitMQ y genera notificaciones (log-based en el lab).
--
-- PATRÓN: Event Consumer
--   Escucha eventos: ticket.created, ticket.assigned, ticket.resolved
--   Genera notificaciones automáticas sin que el servicio productor lo sepa.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Canal de notificación
CREATE TYPE notification_channel AS ENUM ('EMAIL', 'SMS', 'PUSH', 'INTERNAL');

-- Estado de la notificación
CREATE TYPE notification_status AS ENUM ('PENDING', 'SENT', 'FAILED', 'DELIVERED');

-- Tipo de destinatario
CREATE TYPE recipient_type AS ENUM ('CUSTOMER', 'AGENT');

-- Tabla de notificaciones
CREATE TABLE IF NOT EXISTS notifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Tipo de evento que originó esta notificación
    event_type      VARCHAR(100) NOT NULL,

    -- Destinatario
    recipient_id    UUID NOT NULL,
    recipient_type  recipient_type NOT NULL,
    recipient_email VARCHAR(255),

    -- Contenido
    channel         notification_channel NOT NULL DEFAULT 'INTERNAL',
    subject         VARCHAR(300) NOT NULL,
    body            TEXT NOT NULL,

    -- Estado y tracking
    status          notification_status NOT NULL DEFAULT 'PENDING',
    sent_at         TIMESTAMP WITH TIME ZONE,
    delivered_at    TIMESTAMP WITH TIME ZONE,
    error_message   TEXT,

    -- Referencia al evento original (para idempotencia)
    source_event_id UUID UNIQUE,

    -- Auditoría
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications(recipient_id, recipient_type);
CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_event ON notifications(source_event_id);
