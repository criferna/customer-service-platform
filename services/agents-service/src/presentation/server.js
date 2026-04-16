/**
 * =============================================================================
 * PUNTO DE ENTRADA - Agents Service (Express)
 * =============================================================================
 * Microservicio de Gestión de Agentes de Soporte.
 * Publisher + Consumer: publica agent.* events y consume ticket.* events.
 * =============================================================================
 */

const express = require('express');
const cors = require('cors');
const promClient = require('prom-client');
const agentRoutes = require('./routes/agent_routes');
const eventPublisher = require('../infrastructure/messaging/event_publisher');
const { startConsuming } = require('../infrastructure/messaging/event_consumer');

const app = express();
const PORT = process.env.PORT || 3000;
const SERVICE_NAME = process.env.SERVICE_NAME || 'agents-service';

const httpRequestCounter = new promClient.Counter({
  name: 'http_requests_total', help: 'Total HTTP requests',
  labelNames: ['method', 'endpoint', 'status'],
});
const httpRequestDuration = new promClient.Histogram({
  name: 'http_request_duration_seconds', help: 'HTTP request latency',
  labelNames: ['method', 'endpoint'], buckets: [0.01, 0.05, 0.1, 0.5, 1, 5],
});
promClient.collectDefaultMetrics({ prefix: 'agents_' });

app.use(cors());
app.use(express.json());

app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    if (req.path !== '/health' && req.path !== '/metrics') {
      httpRequestCounter.inc({ method: req.method, endpoint: req.path, status: res.statusCode });
      httpRequestDuration.observe({ method: req.method, endpoint: req.path }, duration);
      console.log(JSON.stringify({
        timestamp: new Date().toISOString(), service: SERVICE_NAME, level: 'INFO',
        message: `${req.method} ${req.path} ${res.statusCode} ${duration.toFixed(3)}s`,
        correlation_id: req.headers['x-correlation-id'] || '',
      }));
    }
  });
  next();
});

app.use('/api/v1/agents', agentRoutes);

app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: SERVICE_NAME });
});

app.get('/metrics', async (req, res) => {
  res.set('Content-Type', promClient.register.contentType);
  res.end(await promClient.register.metrics());
});

app.use((err, req, res, _next) => {
  console.error(JSON.stringify({
    timestamp: new Date().toISOString(), service: SERVICE_NAME, level: 'ERROR',
    message: err.message, correlation_id: req.headers['x-correlation-id'] || '',
  }));
  res.status(500).json({ error: 'Internal server error' });
});

async function start() {
  await eventPublisher.connect();
  await startConsuming();
  app.listen(PORT, '0.0.0.0', () => {
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(), service: SERVICE_NAME, level: 'INFO',
      message: `${SERVICE_NAME} listening on port ${PORT}`,
    }));
  });
}

process.on('SIGTERM', async () => {
  await eventPublisher.disconnect();
  process.exit(0);
});

start().catch((err) => { console.error(`Failed to start: ${err}`); process.exit(1); });
