# Customer Service Platform - Microservices Lab

Plataforma de Servicio al Cliente implementada como laboratorio de microservicios. Demuestra patrones de arquitectura distribuida, DDD, Event-Driven Architecture, CI/CD y DevOps.

## Arquitectura

```
                         ┌──────────────────────────────────┐
                         │        API Gateway (Kong)         │
                         │     http://192.168.0.125:8000     │
                         └──┬──────┬──────┬──────┬──────┬───┘
                            │      │      │      │      │
              ┌─────────────┤      │      │      │      ├─────────────┐
              │             │      │      │      │      │             │
        ┌─────▼─────┐ ┌────▼────┐ │ ┌────▼────┐ │ ┌────▼────┐ ┌─────▼─────┐
        │ Customers │ │ Tickets │ │ │ Notifi- │ │ │ Agents  │ │ Knowledge │
        │ Service   │ │ Service │ │ │ cations │ │ │ Service │ │ Service   │
        │ Python/   │ │ Node.js/│ │ │ Python/ │ │ │ Node.js/│ │ Go/Gin    │
        │ FastAPI   │ │ Express │ │ │ FastAPI │ │ │ Express │ │           │
        └─────┬─────┘ └────┬────┘ │ └────┬────┘ │ └────┬────┘ └─────┬─────┘
              │             │      │      │      │      │             │
              │         ┌───▼──────▼──────▼──────▼──────▼───┐        │
              │         │     RabbitMQ (Event Bus)           │        │
              │         │  http://192.168.0.125:15672        │        │
              │         └───────────────────────────────────┘        │
              │                                                       │
        ┌─────▼─────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────▼─────┐
        │ PostgreSQL│ │PostgreSQL│ │PostgreSQL│ │PostgreSQL│ │ PostgreSQL │
        │ customers │ │ tickets  │ │knowledge │ │ notific. │ │  agents    │
        └───────────┘ └──────────┘ └──────────┘ └──────────┘ └────────────┘
```

## Patrones Implementados

| # | Patrón / Principio | Implementación |
|---|---|---|
| 1 | **Microservicios** (Slide 9-10) | 5 servicios independientes con BD propia |
| 2 | **Alta Cohesión** (Slide 16) | Cada servicio = un Bounded Context |
| 3 | **Autonomía** (Slide 17) | Database per Service, contratos API REST |
| 4 | **DDD** (Slide 22-27) | Capas Domain/Application/Infrastructure/Presentation |
| 5 | **Resiliencia** (Slide 19) | Health checks, restart policies, Dead Letter Queues |
| 6 | **Observabilidad** (Slide 20) | Prometheus metrics, JSON logs, Correlation IDs |
| 7 | **Automatización** (Slide 21) | Jenkins CI/CD, Docker Compose IaC |
| 8 | **Event-Driven** (Slide 46) | RabbitMQ Event Bus, Saga coreografiada |
| 9 | **API Gateway** (Slide 46) | Kong: routing, rate limiting, CORS |
| 10 | **Contenedores** (Slide 36-38) | Docker multi-stage builds |
| 11 | **Independencia Tech** (Slide 12) | Python + Node.js + Go |
| 12 | **Consistencia Eventual** | Eventos + datos desnormalizados |
| 13 | **Transactional Outbox** | Tabla outbox_events en cada servicio |
| 14 | **Database per Service** | 5 instancias PostgreSQL aisladas |
| 15 | **DevOps** (Slide 43-44) | Pipeline as Code (Jenkinsfile) |

## Bounded Contexts (DDD)

| Bounded Context | Servicio | Tecnología | Responsabilidad |
|---|---|---|---|
| Gestión de Clientes | `customers-service` | Python / FastAPI | CRUD clientes, eventos customer.* |
| Gestión de Tickets | `tickets-service` | Node.js / Express | Tickets, workflow estados, Saga |
| Base de Conocimiento | `knowledge-service` | Go / Gin | Artículos de ayuda, categorías |
| Notificaciones | `notifications-service` | Python / FastAPI | Consume eventos, genera notificaciones |
| Gestión de Agentes | `agents-service` | Node.js / Express | Agentes, disponibilidad, skills |

## Estructura DDD (cada servicio)

```
service/
├── src/
│   ├── domain/              # Capa de Dominio (entidades, eventos, value objects)
│   │   ├── entities/        # Entidades con identidad y lógica de negocio
│   │   ├── events/          # Eventos de dominio (inmutables)
│   │   └── value_objects/   # Objetos de valor
│   ├── application/         # Capa de Aplicación (casos de uso, DTOs)
│   │   ├── use_cases/       # Orquestación de lógica
│   │   └── dto/             # Data Transfer Objects
│   ├── infrastructure/      # Capa de Infraestructura (BD, messaging)
│   │   ├── database/        # Conexión y modelos de persistencia
│   │   ├── messaging/       # Publisher/Consumer de eventos
│   │   └── repositories/    # Patrón Repository
│   └── presentation/        # Capa de Presentación (API routes, middleware)
│       ├── routes/           # Endpoints HTTP
│       └── middleware/       # Correlation ID, logging
├── Dockerfile               # Multi-stage build
└── tests/
```

## Flujo de Eventos

```
[Cliente crea ticket]
    │
    ▼
tickets-service → publica: ticket.created
    │
    ├──▶ notifications-service → genera notificación al cliente
    │
    └──▶ agents-service → busca agente disponible
              │
              ▼
         tickets-service ← PUT /tickets/:id/assign (agente encontrado)
              │
              ▼
         publica: ticket.assigned
              │
              ├──▶ notifications-service → notifica agente y cliente
              │
              └──▶ agents-service → incrementa active_tickets_count
```

## URLs del Ambiente

| Componente | URL |
|---|---|
| API Gateway (Kong) | http://192.168.0.125:8000 |
| RabbitMQ Management | http://192.168.0.125:15672 |
| Jenkins CI/CD | http://192.168.0.125:9080 |
| Grafana (existente) | http://192.168.0.125:3005 |

## API Endpoints (via Gateway :8000)

```bash
# Customers
GET    /api/v1/customers              # Listar clientes
POST   /api/v1/customers              # Crear cliente
GET    /api/v1/customers/:id          # Obtener cliente
PUT    /api/v1/customers/:id          # Actualizar cliente
DELETE /api/v1/customers/:id          # Eliminar cliente (soft delete)

# Tickets
GET    /api/v1/tickets                # Listar tickets
POST   /api/v1/tickets                # Crear ticket
GET    /api/v1/tickets/:id            # Obtener ticket
PUT    /api/v1/tickets/:id/assign     # Asignar agente
PUT    /api/v1/tickets/:id/start      # Iniciar progreso
PUT    /api/v1/tickets/:id/resolve    # Resolver ticket
PUT    /api/v1/tickets/:id/close      # Cerrar ticket

# Knowledge Base
GET    /api/v1/articles               # Listar artículos
POST   /api/v1/articles               # Crear artículo
GET    /api/v1/articles/:id           # Obtener artículo
PUT    /api/v1/articles/:id           # Actualizar artículo
GET    /api/v1/categories             # Listar categorías
POST   /api/v1/categories             # Crear categoría

# Notifications
GET    /api/v1/notifications          # Listar notificaciones generadas

# Agents
GET    /api/v1/agents                 # Listar agentes
POST   /api/v1/agents                 # Crear agente
GET    /api/v1/agents/:id             # Obtener agente
PUT    /api/v1/agents/:id             # Actualizar agente
PUT    /api/v1/agents/:id/status      # Cambiar estado
GET    /api/v1/agents/available/next  # Buscar agente disponible
```

## Despliegue

```bash
# Setup inicial (primera vez)
chmod +x scripts/*.sh
./scripts/setup-server.sh

# Deploy manual
cd infrastructure
docker compose up -d --build

# Escalar un servicio (ej: 3 instancias de tickets)
docker compose up -d --scale tickets-service=3

# Ver logs
docker compose logs -f tickets-service

# Health check
./scripts/health-check.sh
```

## Credenciales del Lab

| Servicio | Usuario | Password |
|---|---|---|
| RabbitMQ | cs_platform | cs_platform_2024 |
| Jenkins | (ver initial admin password) | `docker exec cs-jenkins cat /var/jenkins_home/secrets/initialAdminPassword` |
