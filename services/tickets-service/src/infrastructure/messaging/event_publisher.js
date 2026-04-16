/**
 * =============================================================================
 * CAPA DE INFRAESTRUCTURA - Event Publisher (RabbitMQ)
 * =============================================================================
 * Publica eventos de dominio del Bounded Context de Tickets al Event Bus.
 *
 * PATRÓN: Event-Driven Architecture
 *   Publica al exchange 'domain.events' con routing key = event_type.
 *   RabbitMQ enruta a las queues suscritas según los bindings configurados.
 *
 * PATRÓN: Resiliencia
 *   - Reconexión automática si se pierde la conexión con RabbitMQ
 *   - Si no puede publicar, loguea el error pero no bloquea la operación
 * =============================================================================
 */

const amqplib = require('amqplib');

const RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://guest:guest@localhost:5672/';
const EXCHANGE_NAME = 'domain.events';
const SERVICE_NAME = process.env.SERVICE_NAME || 'tickets-service';

let connection = null;
let channel = null;

/**
 * Establece conexión con RabbitMQ.
 * Usa reconexión automática en caso de error.
 */
async function connect() {
  try {
    connection = await amqplib.connect(RABBITMQ_URL);
    channel = await connection.createChannel();

    // Reconectar si se cierra la conexión
    connection.on('close', () => {
      console.error(JSON.stringify({
        timestamp: new Date().toISOString(),
        service: SERVICE_NAME,
        level: 'WARN',
        message: 'RabbitMQ connection closed, reconnecting in 5s...',
      }));
      channel = null;
      setTimeout(connect, 5000);
    });

    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      service: SERVICE_NAME,
      level: 'INFO',
      message: 'Connected to RabbitMQ',
    }));
  } catch (err) {
    console.error(JSON.stringify({
      timestamp: new Date().toISOString(),
      service: SERVICE_NAME,
      level: 'ERROR',
      message: `Failed to connect to RabbitMQ: ${err.message}`,
    }));
    // Reintentar conexión
    setTimeout(connect, 5000);
  }
}

/**
 * Publica un evento de dominio al Event Bus.
 *
 * @param {Object} event - Evento de dominio (creado por TicketEvents)
 */
async function publish(event) {
  if (!channel) {
    console.warn(JSON.stringify({
      timestamp: new Date().toISOString(),
      service: SERVICE_NAME,
      level: 'WARN',
      message: `Cannot publish ${event.event_type}: RabbitMQ not connected`,
    }));
    return;
  }

  try {
    const body = Buffer.from(JSON.stringify(event));

    channel.publish(EXCHANGE_NAME, event.event_type, body, {
      persistent: true,                    // Mensaje persiste si RabbitMQ reinicia
      contentType: 'application/json',
      headers: {
        event_type: event.event_type,
        correlation_id: event.correlation_id || '',
        aggregate_type: event.aggregate_type,
        source_service: SERVICE_NAME,
      },
    });

    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      service: SERVICE_NAME,
      level: 'INFO',
      message: `Published event: ${event.event_type}`,
      event_id: event.event_id,
      aggregate_id: event.aggregate_id,
      correlation_id: event.correlation_id,
    }));
  } catch (err) {
    console.error(JSON.stringify({
      timestamp: new Date().toISOString(),
      service: SERVICE_NAME,
      level: 'ERROR',
      message: `Failed to publish ${event.event_type}: ${err.message}`,
    }));
  }
}

/**
 * Cierra la conexión con RabbitMQ.
 */
async function disconnect() {
  if (connection) {
    await connection.close();
  }
}

module.exports = { connect, publish, disconnect };
