-- =============================================================================
-- Knowledge Service - Database Schema (IaC)
-- =============================================================================
-- Bounded Context: Base de Conocimiento
--
-- ENTIDAD: Article (artículos de ayuda / FAQs)
-- ENTIDAD: Category (categorías para organizar artículos)
--
-- Este servicio es mayormente de lectura (read-heavy).
-- Los agentes crean/editan artículos, los clientes los consultan.
-- No tiene dependencias fuertes con otros servicios (Alta Cohesión - Slide 16).
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Categorías de artículos
CREATE TABLE IF NOT EXISTS categories (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Artículos de la base de conocimiento
CREATE TABLE IF NOT EXISTS articles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           VARCHAR(300) NOT NULL,
    content         TEXT NOT NULL,
    category_id     UUID REFERENCES categories(id),

    -- Autor del artículo (referencia local al agente, datos desnormalizados)
    author_agent_id   UUID,
    author_agent_name VARCHAR(200),

    -- Tags para búsqueda (almacenados como array PostgreSQL)
    tags            TEXT[] DEFAULT '{}',

    -- Estado de publicación
    published       BOOLEAN DEFAULT FALSE,

    -- Auditoría
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category_id);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published) WHERE published = TRUE;
CREATE INDEX IF NOT EXISTS idx_articles_tags ON articles USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_articles_title ON articles USING GIN(to_tsvector('spanish', title));

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
INSERT INTO categories (id, name, description) VALUES
    ('f0eebc99-9c0b-4ef8-bb6d-6bb9bd380a66', 'Cuenta', 'Problemas con acceso y cuenta de usuario'),
    ('f1eebc99-9c0b-4ef8-bb6d-6bb9bd380a77', 'Facturación', 'Preguntas sobre cobros y pagos'),
    ('f2eebc99-9c0b-4ef8-bb6d-6bb9bd380a88', 'General', 'Preguntas frecuentes generales')
ON CONFLICT (name) DO NOTHING;

INSERT INTO articles (title, content, category_id, tags, published) VALUES
    ('Cómo recuperar mi contraseña', 'Para recuperar tu contraseña: 1. Ve a la página de login 2. Haz clic en "Olvidé mi contraseña" 3. Ingresa tu email 4. Revisa tu bandeja de entrada', 'f0eebc99-9c0b-4ef8-bb6d-6bb9bd380a66', ARRAY['password', 'login', 'cuenta'], TRUE),
    ('Cómo solicitar un reembolso', 'Para solicitar un reembolso debes crear un ticket de soporte con categoría "Facturación" indicando el monto y fecha del cobro.', 'f1eebc99-9c0b-4ef8-bb6d-6bb9bd380a77', ARRAY['reembolso', 'cobro', 'factura'], TRUE)
ON CONFLICT DO NOTHING;
