/**
 * =============================================================================
 * CAPA DE DOMINIO - Entidad Ticket
 * =============================================================================
 * En DDD, una Entidad tiene identidad propia y ciclo de vida.
 * La entidad Ticket representa una incidencia/caso de soporte.
 *
 * PATRÓN: State Machine
 *   El ticket tiene un workflow de estados con transiciones válidas:
 *   OPEN → ASSIGNED → IN_PROGRESS → RESOLVED → CLOSED
 *                                   → REOPENED → ASSIGNED
 *
 *   Solo se permiten transiciones válidas. Intentar una transición
 *   inválida (ej: OPEN → CLOSED) lanza un error.
 *
 * PATRÓN: Datos Desnormalizados
 *   customer_name, customer_email, assigned_agent_name se almacenan
 *   localmente. NO se hace JOIN al servicio de customers o agents.
 *   Se actualizan vía eventos de RabbitMQ (Consistencia Eventual).
 *
 * REFERENCIA: Slide 17 - Autonomía (no compartir BD)
 * =============================================================================
 */

const { v4: uuidv4 } = require('uuid');

// Transiciones válidas del State Machine.
// Cada estado mapea a los estados a los que puede transicionar.
const VALID_TRANSITIONS = {
  OPEN: ['ASSIGNED'],
  ASSIGNED: ['IN_PROGRESS', 'OPEN'],        // Puede volver a OPEN si el agente se desasigna
  IN_PROGRESS: ['RESOLVED', 'ASSIGNED'],     // Puede reasignarse
  RESOLVED: ['CLOSED', 'REOPENED'],          // Cliente confirma o reabre
  CLOSED: [],                                 // Estado final
  REOPENED: ['ASSIGNED'],                     // Se reasigna un agente
};

class Ticket {
  /**
   * @param {Object} props - Propiedades del ticket
   * @param {string} [props.id] - UUID del ticket (generado si no se provee)
   * @param {string} props.subject - Asunto del ticket
   * @param {string} props.description - Descripción detallada
   * @param {string} [props.status='OPEN'] - Estado actual
   * @param {string} [props.priority='MEDIUM'] - Prioridad
   * @param {string} props.customerId - UUID del cliente (referencia)
   * @param {string} props.customerName - Nombre del cliente (desnormalizado)
   * @param {string} props.customerEmail - Email del cliente (desnormalizado)
   * @param {string} [props.assignedAgentId] - UUID del agente asignado
   * @param {string} [props.assignedAgentName] - Nombre del agente (desnormalizado)
   */
  constructor(props) {
    this.id = props.id || uuidv4();
    this.subject = props.subject;
    this.description = props.description;
    this.status = props.status || 'OPEN';
    this.priority = props.priority || 'MEDIUM';

    // Datos desnormalizados del cliente (copia local, no JOIN)
    this.customerId = props.customerId;
    this.customerName = props.customerName;
    this.customerEmail = props.customerEmail;

    // Datos desnormalizados del agente (copia local)
    this.assignedAgentId = props.assignedAgentId || null;
    this.assignedAgentName = props.assignedAgentName || null;

    // Timestamps del workflow
    this.createdAt = props.createdAt || new Date();
    this.updatedAt = props.updatedAt || new Date();
    this.assignedAt = props.assignedAt || null;
    this.resolvedAt = props.resolvedAt || null;
    this.closedAt = props.closedAt || null;
  }

  /**
   * Transiciona el ticket a un nuevo estado.
   * Valida que la transición sea permitida según el State Machine.
   *
   * @param {string} newStatus - Estado destino
   * @throws {Error} Si la transición no es válida
   */
  transitionTo(newStatus) {
    const allowed = VALID_TRANSITIONS[this.status];
    if (!allowed || !allowed.includes(newStatus)) {
      throw new Error(
        `Invalid transition: ${this.status} → ${newStatus}. ` +
        `Allowed transitions from ${this.status}: [${allowed?.join(', ') || 'none'}]`
      );
    }
    this.status = newStatus;
    this.updatedAt = new Date();
  }

  /**
   * Asigna un agente al ticket (Saga Pattern - paso de asignación).
   *
   * @param {string} agentId - UUID del agente
   * @param {string} agentName - Nombre del agente (desnormalizado)
   */
  assign(agentId, agentName) {
    if (this.status !== 'OPEN' && this.status !== 'REOPENED') {
      throw new Error(`Cannot assign ticket in status ${this.status}`);
    }
    this.assignedAgentId = agentId;
    this.assignedAgentName = agentName;
    this.assignedAt = new Date();
    this.transitionTo('ASSIGNED');
  }

  /**
   * Marca el ticket como resuelto.
   */
  resolve() {
    if (this.status !== 'IN_PROGRESS') {
      throw new Error(`Cannot resolve ticket in status ${this.status}`);
    }
    this.resolvedAt = new Date();
    this.transitionTo('RESOLVED');
  }

  /**
   * Cierra el ticket (confirmación del cliente).
   */
  close() {
    if (this.status !== 'RESOLVED') {
      throw new Error(`Cannot close ticket in status ${this.status}`);
    }
    this.closedAt = new Date();
    this.transitionTo('CLOSED');
  }

  /**
   * Reabre el ticket (el cliente reporta que el problema persiste).
   */
  reopen() {
    if (this.status !== 'RESOLVED') {
      throw new Error(`Cannot reopen ticket in status ${this.status}`);
    }
    this.assignedAgentId = null;
    this.assignedAgentName = null;
    this.resolvedAt = null;
    this.transitionTo('REOPENED');
  }

  /**
   * Actualiza datos desnormalizados del cliente.
   * Llamado cuando se recibe un evento customer.updated de RabbitMQ.
   * Esto implementa la CONSISTENCIA EVENTUAL entre servicios.
   */
  updateCustomerData(customerName, customerEmail) {
    this.customerName = customerName;
    this.customerEmail = customerEmail;
    this.updatedAt = new Date();
  }

  /**
   * Actualiza datos desnormalizados del agente.
   * Llamado cuando se recibe un evento agent.updated de RabbitMQ.
   */
  updateAgentData(agentName) {
    if (this.assignedAgentId) {
      this.assignedAgentName = agentName;
      this.updatedAt = new Date();
    }
  }

  /**
   * Serializa a objeto plano (para persistencia y API).
   */
  toJSON() {
    return {
      id: this.id,
      subject: this.subject,
      description: this.description,
      status: this.status,
      priority: this.priority,
      customer_id: this.customerId,
      customer_name: this.customerName,
      customer_email: this.customerEmail,
      assigned_agent_id: this.assignedAgentId,
      assigned_agent_name: this.assignedAgentName,
      created_at: this.createdAt,
      updated_at: this.updatedAt,
      assigned_at: this.assignedAt,
      resolved_at: this.resolvedAt,
      closed_at: this.closedAt,
    };
  }
}

// Exportar junto con las constantes útiles
module.exports = { Ticket, VALID_TRANSITIONS };
