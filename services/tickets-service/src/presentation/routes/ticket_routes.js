/**
 * =============================================================================
 * CAPA DE PRESENTACIÓN - Rutas API REST (Tickets)
 * =============================================================================
 * Endpoints HTTP del servicio de tickets.
 * Accesibles a través del API Gateway: http://192.168.0.125:8000/api/v1/tickets
 *
 * Contratos del servicio:
 *   POST   /api/v1/tickets              → Crear ticket
 *   GET    /api/v1/tickets              → Listar tickets (con filtros)
 *   GET    /api/v1/tickets/:id          → Obtener ticket por ID
 *   PUT    /api/v1/tickets/:id/assign   → Asignar agente
 *   PUT    /api/v1/tickets/:id/start    → Iniciar progreso
 *   PUT    /api/v1/tickets/:id/resolve  → Resolver ticket
 *   PUT    /api/v1/tickets/:id/close    → Cerrar ticket
 *   PUT    /api/v1/tickets/:id/reopen   → Reabrir ticket
 * =============================================================================
 */

const express = require('express');
const { TicketUseCases } = require('../../application/use_cases/ticket_use_cases');

const router = express.Router();

// Crear un ticket
router.post('/', async (req, res, next) => {
  try {
    const correlationId = req.headers['x-correlation-id'];
    const ticket = await TicketUseCases.createTicket(req.body, correlationId);
    res.status(201).json(ticket);
  } catch (err) {
    next(err);
  }
});

// Listar tickets (con filtros opcionales por query params)
router.get('/', async (req, res, next) => {
  try {
    const filters = {
      skip: parseInt(req.query.skip) || 0,
      limit: Math.min(parseInt(req.query.limit) || 20, 100),
      status: req.query.status || undefined,
      customerId: req.query.customer_id || undefined,
      agentId: req.query.agent_id || undefined,
    };
    const tickets = await TicketUseCases.listTickets(filters);
    res.json(tickets);
  } catch (err) {
    next(err);
  }
});

// Obtener un ticket por ID
router.get('/:id', async (req, res, next) => {
  try {
    const ticket = await TicketUseCases.getTicket(req.params.id);
    if (!ticket) return res.status(404).json({ error: 'Ticket not found' });
    res.json(ticket);
  } catch (err) {
    next(err);
  }
});

// Asignar un agente al ticket (parte de la Saga de asignación)
router.put('/:id/assign', async (req, res, next) => {
  try {
    const correlationId = req.headers['x-correlation-id'];
    const { agent_id, agent_name } = req.body;
    if (!agent_id || !agent_name) {
      return res.status(400).json({ error: 'agent_id and agent_name are required' });
    }
    const ticket = await TicketUseCases.assignTicket(
      req.params.id, agent_id, agent_name, correlationId
    );
    res.json(ticket);
  } catch (err) {
    if (err.message.includes('Cannot assign') || err.message.includes('Invalid transition')) {
      return res.status(422).json({ error: err.message });
    }
    next(err);
  }
});

// Iniciar progreso
router.put('/:id/start', async (req, res, next) => {
  try {
    const correlationId = req.headers['x-correlation-id'];
    const ticket = await TicketUseCases.startProgress(req.params.id, correlationId);
    res.json(ticket);
  } catch (err) {
    if (err.message.includes('Invalid transition')) {
      return res.status(422).json({ error: err.message });
    }
    next(err);
  }
});

// Resolver ticket
router.put('/:id/resolve', async (req, res, next) => {
  try {
    const correlationId = req.headers['x-correlation-id'];
    const ticket = await TicketUseCases.resolveTicket(req.params.id, correlationId);
    res.json(ticket);
  } catch (err) {
    if (err.message.includes('Cannot resolve') || err.message.includes('Invalid transition')) {
      return res.status(422).json({ error: err.message });
    }
    next(err);
  }
});

// Cerrar ticket
router.put('/:id/close', async (req, res, next) => {
  try {
    const correlationId = req.headers['x-correlation-id'];
    const ticket = await TicketUseCases.closeTicket(req.params.id, correlationId);
    res.json(ticket);
  } catch (err) {
    if (err.message.includes('Cannot close') || err.message.includes('Invalid transition')) {
      return res.status(422).json({ error: err.message });
    }
    next(err);
  }
});

// Reabrir ticket
router.put('/:id/reopen', async (req, res, next) => {
  try {
    const correlationId = req.headers['x-correlation-id'];
    const ticket = await TicketUseCases.reopenTicket(req.params.id, correlationId);
    res.json(ticket);
  } catch (err) {
    if (err.message.includes('Cannot reopen') || err.message.includes('Invalid transition')) {
      return res.status(422).json({ error: err.message });
    }
    next(err);
  }
});

module.exports = router;
