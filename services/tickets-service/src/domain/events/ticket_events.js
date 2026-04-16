/**
 * =============================================================================
 * CAPA DE DOMINIO - Eventos de Dominio (Tickets)
 * =============================================================================
 * Eventos que ocurren en el Bounded Context de Tickets.
 * Se publican al Event Bus (RabbitMQ) para que otros servicios reaccionen.
 *
 * Flujo de eventos:
 *   ticket.created   → notifications-service envía notificación al cliente
 *                    → agents-service puede auto-asignar un agente disponible
 *   ticket.assigned  → notifications-service notifica al agente y al cliente
 *                    → agents-service incrementa active_tickets_count
 *   ticket.resolved  → notifications-service notifica al cliente
 *                    → agents-service decrementa active_tickets_count
 *   ticket.closed    → notifications-service confirma al cliente
 *
 * PATRÓN: Saga Coreografiada
 *   No hay un orquestador central. Cada servicio reacciona a los eventos
 *   que le interesan y publica nuevos eventos si es necesario.
 * =============================================================================
 */

const { v4: uuidv4 } = require('uuid');

/**
 * Crea un evento de dominio con estructura estándar.
 *
 * @param {string} eventType - Tipo del evento (routing key en RabbitMQ)
 * @param {string} aggregateId - ID del ticket que generó el evento
 * @param {Object} payload - Datos del evento
 * @param {string} [correlationId] - ID de correlación para tracing
 * @returns {Object} Evento de dominio serializable
 */
function createEvent(eventType, aggregateId, payload, correlationId) {
  return {
    event_id: uuidv4(),
    event_type: eventType,
    aggregate_type: 'Ticket',
    aggregate_id: aggregateId,
    occurred_at: new Date().toISOString(),
    correlation_id: correlationId || null,
    payload,
  };
}

/**
 * Eventos del Bounded Context de Tickets.
 * Cada factory crea un evento con los datos relevantes para los consumidores.
 */
const TicketEvents = {
  /** Se creó un nuevo ticket. Triggers: notificación, posible auto-asignación. */
  created: (ticket, correlationId) =>
    createEvent('ticket.created', ticket.id, {
      id: ticket.id,
      subject: ticket.subject,
      priority: ticket.priority,
      customer_id: ticket.customerId,
      customer_name: ticket.customerName,
      customer_email: ticket.customerEmail,
    }, correlationId),

  /** Se asignó un agente al ticket. */
  assigned: (ticket, correlationId) =>
    createEvent('ticket.assigned', ticket.id, {
      id: ticket.id,
      subject: ticket.subject,
      assigned_agent_id: ticket.assignedAgentId,
      assigned_agent_name: ticket.assignedAgentName,
      customer_id: ticket.customerId,
      customer_name: ticket.customerName,
      customer_email: ticket.customerEmail,
    }, correlationId),

  /** El ticket fue resuelto por el agente. */
  resolved: (ticket, correlationId) =>
    createEvent('ticket.resolved', ticket.id, {
      id: ticket.id,
      subject: ticket.subject,
      assigned_agent_id: ticket.assignedAgentId,
      customer_id: ticket.customerId,
      customer_name: ticket.customerName,
      customer_email: ticket.customerEmail,
      resolved_at: ticket.resolvedAt?.toISOString(),
    }, correlationId),

  /** El ticket fue cerrado (confirmado por el cliente). */
  closed: (ticket, correlationId) =>
    createEvent('ticket.closed', ticket.id, {
      id: ticket.id,
      assigned_agent_id: ticket.assignedAgentId,
      customer_id: ticket.customerId,
      closed_at: ticket.closedAt?.toISOString(),
    }, correlationId),
};

module.exports = { TicketEvents };
