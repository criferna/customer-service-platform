/**
 * Repositorio de Agentes. Abstrae el acceso a datos.
 */
const { pool } = require('../database/connection');
const { Agent } = require('../../domain/entities/agent');

function rowToEntity(row) {
  return new Agent({
    id: row.id,
    firstName: row.first_name,
    lastName: row.last_name,
    email: row.email,
    status: row.status,
    maxTickets: row.max_tickets,
    activeTicketsCount: row.active_tickets_count,
    skills: row.skills || [],
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  });
}

const AgentRepository = {
  async create(agent) {
    const result = await pool.query(
      `INSERT INTO agents (id, first_name, last_name, email, status, max_tickets, active_tickets_count, skills)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *`,
      [agent.id, agent.firstName, agent.lastName, agent.email, agent.status, agent.maxTickets, agent.activeTicketsCount, agent.skills]
    );
    return rowToEntity(result.rows[0]);
  },

  async getById(agentId) {
    const result = await pool.query('SELECT * FROM agents WHERE id = $1', [agentId]);
    return result.rows.length > 0 ? rowToEntity(result.rows[0]) : null;
  },

  async list({ skip = 0, limit = 20, status } = {}) {
    let query = 'SELECT * FROM agents WHERE 1=1';
    const params = [];
    let idx = 1;
    if (status) { query += ` AND status = $${idx++}`; params.push(status); }
    query += ` ORDER BY created_at DESC OFFSET $${idx++} LIMIT $${idx}`;
    params.push(skip, limit);
    const result = await pool.query(query, params);
    return result.rows.map(rowToEntity);
  },

  /** Busca un agente disponible (ONLINE con capacidad). */
  async findAvailable() {
    const result = await pool.query(
      `SELECT * FROM agents WHERE status = 'ONLINE' AND active_tickets_count < max_tickets
       ORDER BY active_tickets_count ASC LIMIT 1`
    );
    return result.rows.length > 0 ? rowToEntity(result.rows[0]) : null;
  },

  async update(agent) {
    const result = await pool.query(
      `UPDATE agents SET first_name=$2, last_name=$3, email=$4, status=$5,
       max_tickets=$6, active_tickets_count=$7, skills=$8, updated_at=$9
       WHERE id=$1 RETURNING *`,
      [agent.id, agent.firstName, agent.lastName, agent.email, agent.status,
       agent.maxTickets, agent.activeTicketsCount, agent.skills, agent.updatedAt]
    );
    return result.rows.length > 0 ? rowToEntity(result.rows[0]) : null;
  },
};

module.exports = { AgentRepository };
