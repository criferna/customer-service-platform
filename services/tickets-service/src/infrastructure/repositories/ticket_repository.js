/**
 * =============================================================================
 * CAPA DE INFRAESTRUCTURA - Repositorio de Tickets
 * =============================================================================
 * Abstrae el acceso a datos para la entidad Ticket.
 *
 * PATRÓN: Repository
 *   Encapsula toda la lógica de persistencia.
 *   La capa de Aplicación (Use Cases) no sabe de SQL ni PostgreSQL.
 *   Si cambiamos de BD, solo cambia este archivo.
 *
 * Convierte entre filas de BD (snake_case) y entidades de dominio (camelCase).
 * =============================================================================
 */

const { pool } = require('../database/connection');
const { Ticket } = require('../../domain/entities/ticket');

/**
 * Convierte una fila de BD a entidad de dominio Ticket.
 */
function rowToEntity(row) {
  return new Ticket({
    id: row.id,
    subject: row.subject,
    description: row.description,
    status: row.status,
    priority: row.priority,
    customerId: row.customer_id,
    customerName: row.customer_name,
    customerEmail: row.customer_email,
    assignedAgentId: row.assigned_agent_id,
    assignedAgentName: row.assigned_agent_name,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    assignedAt: row.assigned_at,
    resolvedAt: row.resolved_at,
    closedAt: row.closed_at,
  });
}

const TicketRepository = {
  /**
   * Crea un nuevo ticket en la BD.
   */
  async create(ticket) {
    const result = await pool.query(
      `INSERT INTO tickets (id, subject, description, status, priority,
                            customer_id, customer_name, customer_email,
                            assigned_agent_id, assigned_agent_name,
                            created_at, updated_at, assigned_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
       RETURNING *`,
      [
        ticket.id, ticket.subject, ticket.description, ticket.status, ticket.priority,
        ticket.customerId, ticket.customerName, ticket.customerEmail,
        ticket.assignedAgentId, ticket.assignedAgentName,
        ticket.createdAt, ticket.updatedAt, ticket.assignedAt,
      ]
    );
    return rowToEntity(result.rows[0]);
  },

  /**
   * Obtiene un ticket por ID.
   */
  async getById(ticketId) {
    const result = await pool.query('SELECT * FROM tickets WHERE id = $1', [ticketId]);
    return result.rows.length > 0 ? rowToEntity(result.rows[0]) : null;
  },

  /**
   * Lista tickets con paginación y filtros opcionales.
   */
  async list({ skip = 0, limit = 20, status, customerId, agentId } = {}) {
    let query = 'SELECT * FROM tickets WHERE 1=1';
    const params = [];
    let paramIndex = 1;

    if (status) {
      query += ` AND status = $${paramIndex++}`;
      params.push(status);
    }
    if (customerId) {
      query += ` AND customer_id = $${paramIndex++}`;
      params.push(customerId);
    }
    if (agentId) {
      query += ` AND assigned_agent_id = $${paramIndex++}`;
      params.push(agentId);
    }

    query += ` ORDER BY created_at DESC OFFSET $${paramIndex++} LIMIT $${paramIndex}`;
    params.push(skip, limit);

    const result = await pool.query(query, params);
    return result.rows.map(rowToEntity);
  },

  /**
   * Actualiza un ticket existente.
   */
  async update(ticket) {
    const result = await pool.query(
      `UPDATE tickets SET
         subject = $2, description = $3, status = $4, priority = $5,
         customer_id = $6, customer_name = $7, customer_email = $8,
         assigned_agent_id = $9, assigned_agent_name = $10,
         updated_at = $11, assigned_at = $12, resolved_at = $13, closed_at = $14
       WHERE id = $1 RETURNING *`,
      [
        ticket.id, ticket.subject, ticket.description, ticket.status, ticket.priority,
        ticket.customerId, ticket.customerName, ticket.customerEmail,
        ticket.assignedAgentId, ticket.assignedAgentName,
        ticket.updatedAt, ticket.assignedAt, ticket.resolvedAt, ticket.closedAt,
      ]
    );
    return result.rows.length > 0 ? rowToEntity(result.rows[0]) : null;
  },
};

module.exports = { TicketRepository };
