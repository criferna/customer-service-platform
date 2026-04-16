/**
 * Pool de conexiones a la BD exclusiva de agents (cs_agents).
 * PATRÓN: Database per Service.
 */
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL || 'postgresql://localhost/cs_agents',
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});

pool.on('error', (err) => {
  console.error(JSON.stringify({
    timestamp: new Date().toISOString(),
    service: process.env.SERVICE_NAME || 'agents-service',
    level: 'ERROR',
    message: `Database pool error: ${err.message}`,
  }));
});

module.exports = { pool };
