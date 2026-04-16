/**
 * =============================================================================
 * CAPA DE INFRAESTRUCTURA - Conexión a Base de Datos (PostgreSQL)
 * =============================================================================
 * Pool de conexiones a la BD exclusiva de tickets (cs_tickets).
 *
 * PATRÓN: Database per Service
 *   Este servicio SOLO se conecta a cs_tickets.
 *   La URL viene por variable de entorno, inyectada por Docker Compose.
 *
 * Usa connection pooling para reutilizar conexiones (eficiencia).
 * =============================================================================
 */

const { Pool } = require('pg');

// La URL de conexión es inyectada por Docker Compose.
// Formato: postgresql://user:pass@host:port/dbname
const pool = new Pool({
  connectionString: process.env.DATABASE_URL || 'postgresql://localhost/cs_tickets',
  max: 10,           // Máximo de conexiones en el pool
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});

// Log de conexiones para debugging
pool.on('error', (err) => {
  console.error(JSON.stringify({
    timestamp: new Date().toISOString(),
    service: process.env.SERVICE_NAME || 'tickets-service',
    level: 'ERROR',
    message: `Database pool error: ${err.message}`,
  }));
});

module.exports = { pool };
