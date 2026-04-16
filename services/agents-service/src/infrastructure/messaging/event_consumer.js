/**
 * =============================================================================
 * Event Consumer para agents-service
 * =============================================================================
 * Consume eventos de tickets para mantener sincronizado:
 *   - active_tickets_count: se incrementa con ticket.assigned,
 *     se decrementa con ticket.resolved / ticket.closed
 *
 * CONSISTENCIA EVENTUAL:
 *   El contador puede estar brevemente desincronizado con la realidad
 *   en tickets-service. Esto es aceptable y esperado en microservicios.
 *
 * MÚLTIPLES INSTANCIAS:
 *   Todas las instancias comparten la misma queue (agents.ticket_events).
 *   RabbitMQ distribuye mensajes en round-robin entre instancias.
 *   Como las operaciones son sobre la BD compartida, no hay conflicto.
 * =============================================================================
 */

const amqplib = require('amqplib');
const { pool } = require('../database/connection');

const RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://guest:guest@localhost:5672/';
const SERVICE_NAME = process.env.SERVICE_NAME || 'agents-service';

async function startConsuming() {
  try {
    const connection = await amqplib.connect(RABBITMQ_URL);
    const channel = await connection.createChannel();
    await channel.prefetch(1);

    await channel.consume('agents.ticket_events', async (msg) => {
      try {
        const event = JSON.parse(msg.content.toString());
        const { event_type, payload, correlation_id } = event;

        console.log(JSON.stringify({
          timestamp: new Date().toISOString(), service: SERVICE_NAME, level: 'INFO',
          message: `Received event: ${event_type}`, correlation_id,
        }));

        if (event_type === 'ticket.assigned' && payload.assigned_agent_id) {
          // Incrementar contador del agente asignado
          await pool.query(
            `UPDATE agents SET active_tickets_count = active_tickets_count + 1,
             status = CASE WHEN active_tickets_count + 1 >= max_tickets THEN 'BUSY' ELSE status END,
             updated_at = NOW()
             WHERE id = $1`,
            [payload.assigned_agent_id]
          );
          console.log(JSON.stringify({
            timestamp: new Date().toISOString(), service: SERVICE_NAME, level: 'INFO',
            message: `Agent ${payload.assigned_agent_id}: incremented active tickets`, correlation_id,
          }));
        }

        if ((event_type === 'ticket.resolved' || event_type === 'ticket.closed') && payload.assigned_agent_id) {
          // Decrementar contador del agente
          await pool.query(
            `UPDATE agents SET active_tickets_count = GREATEST(active_tickets_count - 1, 0),
             status = CASE WHEN status = 'BUSY' AND active_tickets_count - 1 < max_tickets THEN 'ONLINE' ELSE status END,
             updated_at = NOW()
             WHERE id = $1`,
            [payload.assigned_agent_id]
          );
          console.log(JSON.stringify({
            timestamp: new Date().toISOString(), service: SERVICE_NAME, level: 'INFO',
            message: `Agent ${payload.assigned_agent_id}: decremented active tickets`, correlation_id,
          }));
        }

        channel.ack(msg);
      } catch (err) {
        console.error(JSON.stringify({
          timestamp: new Date().toISOString(), service: SERVICE_NAME, level: 'ERROR',
          message: `Error processing ticket event: ${err.message}`,
        }));
        channel.nack(msg, false, false);
      }
    });

    console.log(JSON.stringify({
      timestamp: new Date().toISOString(), service: SERVICE_NAME, level: 'INFO',
      message: 'Started consuming from agents.ticket_events',
    }));

    connection.on('close', () => setTimeout(startConsuming, 5000));
  } catch (err) {
    console.error(JSON.stringify({
      timestamp: new Date().toISOString(), service: SERVICE_NAME, level: 'ERROR',
      message: `Consumer connect failed: ${err.message}`,
    }));
    setTimeout(startConsuming, 5000);
  }
}

module.exports = { startConsuming };
