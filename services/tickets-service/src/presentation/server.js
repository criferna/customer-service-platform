/**
 * =============================================================================
 * PUNTO DE ENTRADA - Tickets Service (Express Application)
 * =============================================================================
 * Configura y arranca el microservicio de Tickets.
 *
 * Componentes:
 *   1. Express server con middleware (CORS, JSON, logging, metrics)
 *   2. Rutas de la API de tickets
 *   3. Health check y métricas Prometheus
 *   4. Event consumer (RabbitMQ) para consistencia eventual
 *   5. Graceful shutdown
 *
 * INDEPENDENCIA TECNOLÓGICA (Slide 12):
 *   Este servicio usa Node.js/Express mientras customers-service usa Python/FastAPI.
 *   Ambos exponen APIs REST compatibles y se comunican vía RabbitMQ.
 *   Demuestra que cada equipo puede elegir su stack tecnológico.
 * =============================================================================
 */

const express = require('express');
const cors = require('cors');
const promClient = require('prom-client');
const ticketRoutes = require('./routes/ticket_routes');
const eventPublisher = require('../infrastructure/messaging/event_publisher');
const { startConsuming } = require('../infrastructure/messaging/event_consumer');

const app = express();
const PORT = process.env.PORT || 3000;
const SERVICE_NAME = process.env.SERVICE_NAME || 'tickets-service';

// =============================================================================
// Métricas Prometheus
// =============================================================================
const httpRequestCounter = new promClient.Counter({
  name: 'http_requests_total',
  help: 'Total HTTP requests',
  labelNames: ['method', 'endpoint', 'status'],
});

const httpRequestDuration = new promClient.Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request latency',
  labelNames: ['method', 'endpoint'],
  buckets: [0.01, 0.05, 0.1, 0.5, 1, 5],
});

// Recolectar métricas por defecto (CPU, memoria, event loop)
promClient.collectDefaultMetrics({ prefix: 'tickets_' });

// =============================================================================
// Middleware
// =============================================================================
app.use(cors());
app.use(express.json());

// Middleware de logging y métricas
app.use((req, res, next) => {
  const start = Date.now();

  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;

    // No registrar health checks ni métricas
    if (req.path !== '/health' && req.path !== '/metrics') {
      httpRequestCounter.inc({
        method: req.method,
        endpoint: req.path,
        status: res.statusCode,
      });
      httpRequestDuration.observe(
        { method: req.method, endpoint: req.path },
        duration
      );

      console.log(JSON.stringify({
        timestamp: new Date().toISOString(),
        service: SERVICE_NAME,
        level: 'INFO',
        message: `${req.method} ${req.path} ${res.statusCode} ${duration.toFixed(3)}s`,
        correlation_id: req.headers['x-correlation-id'] || '',
      }));
    }
  });

  next();
});

// =============================================================================
// Rutas
// =============================================================================
app.use('/api/v1/tickets', ticketRoutes);

// Health check para Docker y Kong
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: SERVICE_NAME });
});

// Métricas Prometheus
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', promClient.register.contentType);
  res.end(await promClient.register.metrics());
});

// Error handler global
app.use((err, req, res, _next) => {
  console.error(JSON.stringify({
    timestamp: new Date().toISOString(),
    service: SERVICE_NAME,
    level: 'ERROR',
    message: err.message,
    stack: err.stack,
    correlation_id: req.headers['x-correlation-id'] || '',
  }));
  res.status(500).json({ error: 'Internal server error' });
});

// =============================================================================
// Startup
// =============================================================================
async function start() {
  // Conectar al Event Bus (publisher + consumer)
  await eventPublisher.connect();
  await startConsuming();

  app.listen(PORT, '0.0.0.0', () => {
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      service: SERVICE_NAME,
      level: 'INFO',
      message: `${SERVICE_NAME} listening on port ${PORT}`,
    }));
  });
}

// Graceful shutdown: cerrar conexiones limpiamente
process.on('SIGTERM', async () => {
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    service: SERVICE_NAME,
    level: 'INFO',
    message: 'SIGTERM received, shutting down gracefully...',
  }));
  await eventPublisher.disconnect();
  process.exit(0);
});

start().catch((err) => {
  console.error(`Failed to start ${SERVICE_NAME}:`, err);
  process.exit(1);
});
