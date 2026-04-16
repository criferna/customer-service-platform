/**
 * Rutas API REST para el servicio de Agentes.
 */
const express = require('express');
const { v4: uuidv4 } = require('uuid');
const { Agent } = require('../../domain/entities/agent');
const { AgentRepository } = require('../../infrastructure/repositories/agent_repository');
const eventPublisher = require('../../infrastructure/messaging/event_publisher');

const router = express.Router();

// Crear agente
router.post('/', async (req, res, next) => {
  try {
    const { first_name, last_name, email, max_tickets, skills } = req.body;
    if (!first_name || !last_name || !email) {
      return res.status(400).json({ error: 'first_name, last_name and email are required' });
    }
    const agent = new Agent({ firstName: first_name, lastName: last_name, email, maxTickets: max_tickets || 5, skills: skills || [] });
    const saved = await AgentRepository.create(agent);

    await eventPublisher.publish({
      event_id: uuidv4(), event_type: 'agent.created', aggregate_type: 'Agent',
      aggregate_id: saved.id, occurred_at: new Date().toISOString(),
      correlation_id: req.headers['x-correlation-id'],
      payload: { id: saved.id, first_name: saved.firstName, last_name: saved.lastName, email: saved.email },
    });

    res.status(201).json(saved.toJSON());
  } catch (err) { next(err); }
});

// Listar agentes
router.get('/', async (req, res, next) => {
  try {
    const agents = await AgentRepository.list({
      skip: parseInt(req.query.skip) || 0,
      limit: Math.min(parseInt(req.query.limit) || 20, 100),
      status: req.query.status,
    });
    res.json(agents.map(a => a.toJSON()));
  } catch (err) { next(err); }
});

// Obtener agente por ID
router.get('/:id', async (req, res, next) => {
  try {
    const agent = await AgentRepository.getById(req.params.id);
    if (!agent) return res.status(404).json({ error: 'Agent not found' });
    res.json(agent.toJSON());
  } catch (err) { next(err); }
});

// Buscar un agente disponible (para la Saga de asignación)
router.get('/available/next', async (req, res, next) => {
  try {
    const agent = await AgentRepository.findAvailable();
    if (!agent) return res.status(404).json({ error: 'No available agents' });
    res.json(agent.toJSON());
  } catch (err) { next(err); }
});

// Cambiar estado del agente
router.put('/:id/status', async (req, res, next) => {
  try {
    const { status } = req.body;
    const agent = await AgentRepository.getById(req.params.id);
    if (!agent) return res.status(404).json({ error: 'Agent not found' });

    agent.setStatus(status);
    const updated = await AgentRepository.update(agent);

    await eventPublisher.publish({
      event_id: uuidv4(), event_type: 'agent.status_changed', aggregate_type: 'Agent',
      aggregate_id: updated.id, occurred_at: new Date().toISOString(),
      correlation_id: req.headers['x-correlation-id'],
      payload: { id: updated.id, status: updated.status, is_available: updated.isAvailable },
    });

    res.json(updated.toJSON());
  } catch (err) {
    if (err.message.includes('Invalid status')) return res.status(422).json({ error: err.message });
    next(err);
  }
});

// Actualizar agente
router.put('/:id', async (req, res, next) => {
  try {
    const agent = await AgentRepository.getById(req.params.id);
    if (!agent) return res.status(404).json({ error: 'Agent not found' });

    const { first_name, last_name, email, max_tickets, skills } = req.body;
    if (first_name) agent.firstName = first_name;
    if (last_name) agent.lastName = last_name;
    if (email) agent.email = email;
    if (max_tickets) agent.maxTickets = max_tickets;
    if (skills) agent.skills = skills;
    agent.updatedAt = new Date();

    const updated = await AgentRepository.update(agent);

    await eventPublisher.publish({
      event_id: uuidv4(), event_type: 'agent.updated', aggregate_type: 'Agent',
      aggregate_id: updated.id, occurred_at: new Date().toISOString(),
      correlation_id: req.headers['x-correlation-id'],
      payload: { id: updated.id, first_name: updated.firstName, last_name: updated.lastName, email: updated.email },
    });

    res.json(updated.toJSON());
  } catch (err) { next(err); }
});

module.exports = router;
