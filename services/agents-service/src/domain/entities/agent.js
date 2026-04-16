/**
 * =============================================================================
 * CAPA DE DOMINIO - Entidad Agent
 * =============================================================================
 * Agente de soporte que atiende tickets de clientes.
 *
 * SINCRONIZACIÓN VIA EVENTOS:
 *   El campo active_tickets_count se mantiene sincronizado con tickets-service
 *   a través de eventos de RabbitMQ:
 *     - ticket.assigned → incrementa active_tickets_count
 *     - ticket.resolved / ticket.closed → decrementa active_tickets_count
 *
 *   Esto es CONSISTENCIA EVENTUAL: puede haber un breve delay entre
 *   la asignación del ticket y la actualización del contador.
 *   Esto es aceptable porque la precisión absoluta no es crítica aquí.
 *
 * DISPONIBILIDAD:
 *   Un agente está "disponible" si:
 *     - status es ONLINE
 *     - active_tickets_count < max_tickets
 * =============================================================================
 */

const { v4: uuidv4 } = require('uuid');

const VALID_STATUSES = ['ONLINE', 'OFFLINE', 'BUSY', 'ON_BREAK'];

class Agent {
  constructor(props) {
    this.id = props.id || uuidv4();
    this.firstName = props.firstName;
    this.lastName = props.lastName;
    this.email = props.email;
    this.status = props.status || 'OFFLINE';
    this.maxTickets = props.maxTickets || 5;
    this.activeTicketsCount = props.activeTicketsCount || 0;
    this.skills = props.skills || [];
    this.createdAt = props.createdAt || new Date();
    this.updatedAt = props.updatedAt || new Date();
  }

  get fullName() {
    return `${this.firstName} ${this.lastName}`;
  }

  /** Un agente puede recibir tickets si está ONLINE y tiene capacidad. */
  get isAvailable() {
    return this.status === 'ONLINE' && this.activeTicketsCount < this.maxTickets;
  }

  /** Cambia el estado del agente. */
  setStatus(newStatus) {
    if (!VALID_STATUSES.includes(newStatus)) {
      throw new Error(`Invalid status: ${newStatus}. Valid: ${VALID_STATUSES.join(', ')}`);
    }
    this.status = newStatus;
    this.updatedAt = new Date();
  }

  /**
   * Incrementa el contador de tickets activos.
   * Llamado cuando se recibe un evento ticket.assigned para este agente.
   */
  incrementActiveTickets() {
    this.activeTicketsCount++;
    if (this.activeTicketsCount >= this.maxTickets) {
      this.status = 'BUSY';
    }
    this.updatedAt = new Date();
  }

  /**
   * Decrementa el contador de tickets activos.
   * Llamado cuando se recibe un evento ticket.resolved o ticket.closed.
   */
  decrementActiveTickets() {
    if (this.activeTicketsCount > 0) {
      this.activeTicketsCount--;
    }
    if (this.status === 'BUSY' && this.activeTicketsCount < this.maxTickets) {
      this.status = 'ONLINE';
    }
    this.updatedAt = new Date();
  }

  toJSON() {
    return {
      id: this.id,
      first_name: this.firstName,
      last_name: this.lastName,
      email: this.email,
      status: this.status,
      max_tickets: this.maxTickets,
      active_tickets_count: this.activeTicketsCount,
      skills: this.skills,
      is_available: this.isAvailable,
      created_at: this.createdAt,
      updated_at: this.updatedAt,
    };
  }
}

module.exports = { Agent, VALID_STATUSES };
