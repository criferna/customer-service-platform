/**
 * Event Publisher para agents-service.
 * Mismo patrón que tickets-service — publica al exchange domain.events.
 */
const amqplib = require('amqplib');

const RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://guest:guest@localhost:5672/';
const EXCHANGE_NAME = 'domain.events';
const SERVICE_NAME = process.env.SERVICE_NAME || 'agents-service';

let connection = null;
let channel = null;

async function connect() {
  try {
    connection = await amqplib.connect(RABBITMQ_URL);
    channel = await connection.createChannel();
    connection.on('close', () => { channel = null; setTimeout(connect, 5000); });
    console.log(JSON.stringify({ timestamp: new Date().toISOString(), service: SERVICE_NAME, level: 'INFO', message: 'Connected to RabbitMQ (publisher)' }));
  } catch (err) {
    console.error(JSON.stringify({ timestamp: new Date().toISOString(), service: SERVICE_NAME, level: 'ERROR', message: `RabbitMQ publisher connect failed: ${err.message}` }));
    setTimeout(connect, 5000);
  }
}

async function publish(event) {
  if (!channel) return;
  try {
    const body = Buffer.from(JSON.stringify(event));
    channel.publish(EXCHANGE_NAME, event.event_type, body, {
      persistent: true,
      contentType: 'application/json',
      headers: { event_type: event.event_type, correlation_id: event.correlation_id || '', source_service: SERVICE_NAME },
    });
  } catch (err) {
    console.error(JSON.stringify({ timestamp: new Date().toISOString(), service: SERVICE_NAME, level: 'ERROR', message: `Publish failed: ${err.message}` }));
  }
}

async function disconnect() { if (connection) await connection.close(); }

module.exports = { connect, publish, disconnect };
