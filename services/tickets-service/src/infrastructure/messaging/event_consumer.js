/**
 * =============================================================================
 * CAPA DE INFRAESTRUCTURA - Event Consumer (RabbitMQ)
 * =============================================================================
 * Consume eventos de otros Bounded Contexts para mantener datos sincronizados.
 *
 * PATRÓN: Consistencia Eventual
 *   Cuando customers-service actualiza un cliente, publica customer.updated.
 *   Este consumidor recibe el evento y actualiza la copia local del cliente
 *   en los tickets que lo referencian. Lo mismo para agent.updated.
 *
 *   Esto mantiene los datos desnormalizados sincronizados SIN acoplar servicios.
 *   El delay entre la actualización y la sincronización es de milisegundos
 *   (consistencia eventual, no inmediata).
 *
 * QUEUES CONSUMIDAS:
 *   - tickets.customer_events: eventos customer.created, customer.updated
 *   - tickets.agent_events: eventos agent.updated, agent.available
 *
 * NOTA SOBRE MÚLTIPLES INSTANCIAS:
 *   Si hay 3 instancias de tickets-service, RabbitMQ distribuye los mensajes
 *   entre las instancias (round-robin). Cada mensaje lo procesa UNA sola instancia.
 *   Esto es posible porque todas las instancias comparten la MISMA queue.
 * =============================================================================
 */

const amqplib = require('amqplib');
const { pool } = require('../database/connection');

const RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://guest:guest@localhost:5672/';
const SERVICE_NAME = process.env.SERVICE_NAME || 'tickets-service';

let connection = null;
let channel = null;

/**
 * Conecta y comienza a consumir eventos.
 */
async function startConsuming() {
  try {
    connection = await amqplib.connect(RABBITMQ_URL);
    channel = await connection.createChannel();

    // Prefetch = 1: procesar un mensaje a la vez por instancia.
    // Esto asegura distribución equitativa entre múltiples instancias.
    await channel.prefetch(1);

    // Consumir eventos de Customer
    await channel.consume('tickets.customer_events', handleCustomerEvent, { noAck: false });

    // Consumir eventos de Agent
    await channel.consume('tickets.agent_events', handleAgentEvent, { noAck: false });

    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      service: SERVICE_NAME,
      level: 'INFO',
      message: 'Started consuming events from: tickets.customer_events, tickets.agent_events',
    }));

    // Reconexión automática
    connection.on('close', () => {
      console.warn(JSON.stringify({
        timestamp: new Date().toISOString(),
        service: SERVICE_NAME,
        level: 'WARN',
        message: 'RabbitMQ consumer connection closed, reconnecting in 5s...',
      }));
      setTimeout(startConsuming, 5000);
    });
  } catch (err) {
    console.error(JSON.stringify({
      timestamp: new Date().toISOString(),
      service: SERVICE_NAME,
      level: 'ERROR',
      message: `Failed to start consuming: ${err.message}`,
    }));
    setTimeout(startConsuming, 5000);
  }
}

/**
 * Procesa eventos de Customer (customer.created, customer.updated, customer.deleted).
 * Actualiza las copias locales de datos de cliente en los tickets.
 *
 * CONSISTENCIA EVENTUAL: cuando el nombre de un cliente cambia en customers-service,
 * este handler actualiza customer_name en todos los tickets de ese cliente.
 */
async function handleCustomerEvent(msg) {
  try {
    const event = JSON.parse(msg.content.toString());
    const { event_type, payload, correlation_id } = event;

    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      service: SERVICE_NAME,
      level: 'INFO',
      message: `Received event: ${event_type}`,
      correlation_id,
      customer_id: payload.id,
    }));

    if (event_type === 'customer.updated') {
      // Actualizar datos desnormalizados del cliente en todos sus tickets.
      // Esto es la sincronización de consistencia eventual.
      await pool.query(
        `UPDATE tickets
         SET customer_name = $1 || ' ' || $2,
             customer_email = $3,
             updated_at = NOW()
         WHERE customer_id = $4`,
        [payload.first_name, payload.last_name, payload.email, payload.id]
      );

      console.log(JSON.stringify({
        timestamp: new Date().toISOString(),
        service: SERVICE_NAME,
        level: 'INFO',
        message: `Updated denormalized customer data for customer ${payload.id}`,
        correlation_id,
      }));
    }

    // ACK: confirmar que el mensaje fue procesado exitosamente.
    // Si no hacemos ACK, RabbitMQ reentregará el mensaje a otra instancia.
    channel.ack(msg);
  } catch (err) {
    console.error(JSON.stringify({
      timestamp: new Date().toISOString(),
      service: SERVICE_NAME,
      level: 'ERROR',
      message: `Error processing customer event: ${err.message}`,
    }));
    // NACK con requeue=false: el mensaje va a la Dead Letter Exchange (DLX).
    // Esto evita loops infinitos de mensajes fallidos.
    channel.nack(msg, false, false);
  }
}

/**
 * Procesa eventos de Agent (agent.updated, agent.status_changed).
 * Actualiza las copias locales de datos de agente en los tickets.
 */
async function handleAgentEvent(msg) {
  try {
    const event = JSON.parse(msg.content.toString());
    const { event_type, payload, correlation_id } = event;

    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      service: SERVICE_NAME,
      level: 'INFO',
      message: `Received event: ${event_type}`,
      correlation_id,
      agent_id: payload.id,
    }));

    if (event_type === 'agent.updated') {
      await pool.query(
        `UPDATE tickets
         SET assigned_agent_name = $1 || ' ' || $2,
             updated_at = NOW()
         WHERE assigned_agent_id = $3`,
        [payload.first_name, payload.last_name, payload.id]
      );
    }

    channel.ack(msg);
  } catch (err) {
    console.error(JSON.stringify({
      timestamp: new Date().toISOString(),
      service: SERVICE_NAME,
      level: 'ERROR',
      message: `Error processing agent event: ${err.message}`,
    }));
    channel.nack(msg, false, false);
  }
}

module.exports = { startConsuming };
