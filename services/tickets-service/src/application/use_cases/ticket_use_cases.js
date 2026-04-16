/**
 * =============================================================================
 * CAPA DE APLICACIÓN - Casos de Uso de Tickets
 * =============================================================================
 * Orquesta la lógica de la aplicación para el Bounded Context de Tickets.
 *
 * PRINCIPIO DDD: Los Use Cases coordinan, no contienen lógica de negocio.
 *   La lógica del State Machine (transiciones de estado) vive en la entidad Ticket.
 *   Los Use Cases solo coordinan: repositorio ↔ dominio ↔ eventos.
 *
 * PATRÓN: Saga Coreografiada
 *   La creación de un ticket publica ticket.created.
 *   agents-service reacciona asignando un agente y publica agent.assigned.
 *   Este servicio reacciona asignando el agente al ticket.
 *   No hay un orquestador central — cada servicio reacciona a eventos.
 * =============================================================================
 */

const { Ticket } = require('../../domain/entities/ticket');
const { TicketEvents } = require('../../domain/events/ticket_events');
const { TicketRepository } = require('../../infrastructure/repositories/ticket_repository');
const eventPublisher = require('../../infrastructure/messaging/event_publisher');

const SERVICE_NAME = process.env.SERVICE_NAME || 'tickets-service';

function log(level, message, extra = {}) {
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    service: SERVICE_NAME,
    level,
    message,
    ...extra,
  }));
}

const TicketUseCases = {
  /**
   * Caso de Uso: Crear un nuevo ticket.
   *
   * Flujo:
   *   1. Crear entidad Ticket (dominio)
   *   2. Persistir en BD (infraestructura)
   *   3. Publicar ticket.created al Event Bus
   *   4. agents-service reacciona al evento (Saga)
   */
  async createTicket(data, correlationId) {
    log('INFO', 'Creating ticket', { subject: data.subject, correlation_id: correlationId });

    // 1. Crear entidad de dominio
    const ticket = new Ticket({
      subject: data.subject,
      description: data.description,
      priority: data.priority || 'MEDIUM',
      customerId: data.customer_id,
      customerName: data.customer_name,
      customerEmail: data.customer_email,
    });

    // 2. Persistir
    const saved = await TicketRepository.create(ticket);

    // 3. Publicar evento — otros servicios reaccionan
    const event = TicketEvents.created(saved, correlationId);
    await eventPublisher.publish(event);

    log('INFO', 'Ticket created', { ticket_id: saved.id, correlation_id: correlationId });
    return saved.toJSON();
  },

  /**
   * Caso de Uso: Obtener un ticket por ID.
   */
  async getTicket(ticketId) {
    const ticket = await TicketRepository.getById(ticketId);
    return ticket ? ticket.toJSON() : null;
  },

  /**
   * Caso de Uso: Listar tickets con filtros.
   */
  async listTickets(filters = {}) {
    const tickets = await TicketRepository.list(filters);
    return tickets.map((t) => t.toJSON());
  },

  /**
   * Caso de Uso: Asignar un agente al ticket.
   *
   * Este es un paso de la SAGA de creación de tickets:
   *   ticket.created → agents-service selecciona agente → este endpoint asigna
   */
  async assignTicket(ticketId, agentId, agentName, correlationId) {
    const ticket = await TicketRepository.getById(ticketId);
    if (!ticket) throw new Error('Ticket not found');

    // Lógica de negocio en la entidad (DDD)
    ticket.assign(agentId, agentName);

    const updated = await TicketRepository.update(ticket);

    // Notificar al resto del sistema
    const event = TicketEvents.assigned(updated, correlationId);
    await eventPublisher.publish(event);

    log('INFO', 'Ticket assigned', {
      ticket_id: ticketId,
      agent_id: agentId,
      correlation_id: correlationId,
    });
    return updated.toJSON();
  },

  /**
   * Caso de Uso: Marcar ticket como en progreso.
   */
  async startProgress(ticketId, correlationId) {
    const ticket = await TicketRepository.getById(ticketId);
    if (!ticket) throw new Error('Ticket not found');

    ticket.transitionTo('IN_PROGRESS');
    const updated = await TicketRepository.update(ticket);
    return updated.toJSON();
  },

  /**
   * Caso de Uso: Resolver un ticket.
   */
  async resolveTicket(ticketId, correlationId) {
    const ticket = await TicketRepository.getById(ticketId);
    if (!ticket) throw new Error('Ticket not found');

    ticket.resolve();
    const updated = await TicketRepository.update(ticket);

    const event = TicketEvents.resolved(updated, correlationId);
    await eventPublisher.publish(event);

    log('INFO', 'Ticket resolved', { ticket_id: ticketId, correlation_id: correlationId });
    return updated.toJSON();
  },

  /**
   * Caso de Uso: Cerrar un ticket.
   */
  async closeTicket(ticketId, correlationId) {
    const ticket = await TicketRepository.getById(ticketId);
    if (!ticket) throw new Error('Ticket not found');

    ticket.close();
    const updated = await TicketRepository.update(ticket);

    const event = TicketEvents.closed(updated, correlationId);
    await eventPublisher.publish(event);

    log('INFO', 'Ticket closed', { ticket_id: ticketId, correlation_id: correlationId });
    return updated.toJSON();
  },

  /**
   * Caso de Uso: Reabrir un ticket.
   */
  async reopenTicket(ticketId, correlationId) {
    const ticket = await TicketRepository.getById(ticketId);
    if (!ticket) throw new Error('Ticket not found');

    ticket.reopen();
    const updated = await TicketRepository.update(ticket);
    return updated.toJSON();
  },
};

module.exports = { TicketUseCases };
