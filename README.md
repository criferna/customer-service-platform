# Customer Service Platform - Microservices Lab

Plataforma de Servicio al Cliente implementada como laboratorio de microservicios. Demuestra patrones de arquitectura distribuida, DDD, Event-Driven Architecture, CI/CD y DevOps.

## Versiones

Este proyecto tiene **dos implementaciones** del mismo sistema:

| | Docker (on-premise) | AWS (serverless) |
|---|---|---|
| **Compute** | 5 contenedores Docker | 8 AWS Lambda functions |
| **API Gateway** | Kong | Amazon API Gateway |
| **Base de datos** | 5 PostgreSQL | 6 DynamoDB tables |
| **Event Bus** | RabbitMQ | SNS + SQS |
| **Observabilidad** | Prometheus + Grafana | CloudWatch |
| **CI/CD** | Jenkins | GitHub Actions |
| **IaC** | Docker Compose | Terraform |
| **Tecnologías** | Python + Node.js + Go | Python 3.12 (todas) |

---

## Arquitectura AWS (Serverless)

```
                    ┌─────────────────────────────────────┐
                    │     Amazon API Gateway (REST)        │
                    │     lab-ms-api                       │
                    └──┬──────┬──────┬──────┬──────┬──────┘
                       │      │      │      │      │
         ┌─────────────┤      │      │      │      ├──────────────┐
         │             │      │      │      │      │              │
   ┌─────▼─────┐ ┌────▼────┐ │ ┌────▼────┐ │ ┌────▼────┐ ┌──────▼──────┐
   │ Customers │ │ Tickets │ │ │ Notifi- │ │ │ Agents  │ │  Knowledge  │
   │  Lambda   │ │ Lambda  │ │ │ cations │ │ │ Lambda  │ │   Lambda    │
   │           │ │         │ │ │ Lambda  │ │ │         │ │ categories  │
   │           │ │         │ │ │(read)   │ │ │Strategy │ │ + articles  │
   └─────┬─────┘ └────┬────┘ │ └─────────┘ │ └────┬────┘ └──────┬──────┘
         │             │      │             │      │              │
         │        ┌────▼──────▼─────────────▼──────▼────┐        │
         │        │     SNS Topic: lab-ms-domain-events  │        │
         │        │        (Observer Pattern)            │        │
         │        └──┬──────────────┬───────────────┬────┘        │
         │           │              │               │             │
         │    ┌──────▼──────┐ ┌────▼──────┐ ┌──────▼──────┐      │
         │    │ SQS: notif- │ │ SQS:      │ │ SQS: agents │      │
         │    │ ticket-evts │ │ tickets-  │ │ ticket-evts │      │
         │    └──────┬──────┘ │ cust-evts │ └──────┬──────┘      │
         │           │        └────┬──────┘        │             │
         │    ┌──────▼──────┐ ┌────▼──────┐ ┌──────▼──────┐      │
         │    │ Notif.      │ │ Tickets   │ │ Agents      │      │
         │    │ Consumer    │ │ Consumer  │ │ Consumer    │      │
         │    │ (Factory)   │ │           │ │             │      │
         │    └──────┬──────┘ └────┬──────┘ └──────┬──────┘      │
         │           │             │               │             │
   ┌─────▼─────┐ ┌──▼───────┐ ┌───▼─────┐ ┌──────▼──────┐ ┌────▼────────┐
   │ DynamoDB  │ │ DynamoDB │ │DynamoDB │ │  DynamoDB   │ │  DynamoDB   │
   │ customers │ │ notific. │ │ tickets │ │   agents    │ │ categories  │
   └───────────┘ └──────────┘ └─────────┘ └─────────────┘ │ + articles  │
                                                          └─────────────┘
```

### Patrones de Diseño (AWS Lambda)

| # | Patrón | Tipo | Implementación |
|---|---|---|---|
| 1 | **Singleton** | Creacional | `shared/singleton.py` — DynamoDBClient, SNSClient, SQSClient reutilizados en warm starts |
| 2 | **Factory** | Creacional | `shared/factory.py` — NotificationFactory crea InternalNotifier, EmailNotifier o SnsNotifier según env |
| 3 | **Decorator** | Estructural | `shared/decorator.py` — `@lambda_handler()` apila error handling, correlation ID, logging, JSON parsing |
| 4 | **Observer** | Comportamiento | `shared/observer.py` — DomainEventPublisher via SNS, SQS queues como observers con filter policies |
| 5 | **Strategy** | Comportamiento | `shared/strategy.py` — LeastLoaded, RoundRobin, SkillBased para asignación de agentes |

### Estructura AWS

```
aws-lambdas/
├── shared/                          # Lambda Layer (5 patrones de diseño)
│   ├── __init__.py
│   ├── singleton.py                 # Patrón Singleton
│   ├── factory.py                   # Patrón Factory
│   ├── decorator.py                 # Patrón Decorator
│   ├── observer.py                  # Patrón Observer
│   └── strategy.py                  # Patrón Strategy
├── functions/
│   ├── customers/handler.py         # API: CRUD clientes
│   ├── tickets/handler.py           # API: workflow tickets (State Machine)
│   ├── agents/handler.py            # API: agentes + Strategy assignment
│   ├── notifications/handler.py     # API: consulta notificaciones (read-only)
│   ├── knowledge/handler.py         # API: categorías + artículos
│   ├── notifications-consumer/      # Consumer: crea notificaciones (Factory)
│   ├── tickets-consumer/            # Consumer: propaga datos desnormalizados
│   └── agents-consumer/             # Consumer: contadores de carga (atomic)
terraform/
├── versions.tf                      # Providers + backend config
├── variables.tf                     # Variables configurables
├── dynamodb.tf                      # 6 tablas DynamoDB con GSIs
├── sns_sqs.tf                       # SNS topic + 3 SQS queues + DLQs
├── iam.tf                           # Roles y policies (least privilege)
├── lambda.tf                        # 8 Lambda functions + layer + event mappings
├── api_gateway.tf                   # REST API con proxy integration
└── outputs.tf                       # URLs, ARNs, nombres
.github/workflows/
├── infra.yml                        # CI/CD: Terraform plan/apply
└── deploy.yml                       # CI/CD: Lambda package + deploy
```

### Deploy AWS

```bash
# 1. Configurar credenciales AWS
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."

# 2. Copiar y editar variables
cp terraform/terraform.tfvars.example terraform/terraform.tfvars

# 3. Inicializar y aplicar
cd terraform
terraform init
terraform plan
terraform apply

# 4. Obtener URL del API
terraform output api_gateway_url
# → https://xxxxxxxxxx.execute-api.us-east-2.amazonaws.com/dev

# 5. Probar
curl https://xxxxxxxxxx.execute-api.us-east-2.amazonaws.com/dev/api/v1/customers
```

### CI/CD (GitHub Actions)

| Workflow | Trigger | Acción |
|---|---|---|
| `infra.yml` | Cambios en `terraform/` | PR: `terraform plan` → Apply en merge a main |
| `deploy.yml` | Cambios en `aws-lambdas/` | Lint → Package → Deploy Lambdas |

**Secrets requeridos:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

---

## Arquitectura Docker (On-Premise)

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

### Deploy Docker

```bash
cd infrastructure
docker compose up -d --build
docker compose logs -f tickets-service
```

### URLs Docker

| Componente | URL |
|---|---|
| API Gateway (Kong) | http://192.168.0.125:8000 |
| RabbitMQ Management | http://192.168.0.125:15672 |
| Jenkins CI/CD | http://192.168.0.125:9080 |

---

## Bounded Contexts (DDD)

| Bounded Context | Responsabilidad | Docker | AWS |
|---|---|---|---|
| Gestión de Clientes | CRUD clientes, soft delete | Python/FastAPI + PostgreSQL | Lambda + DynamoDB |
| Gestión de Tickets | Workflow tickets, State Machine | Node.js/Express + PostgreSQL | Lambda + DynamoDB |
| Base de Conocimiento | Artículos y categorías | Go/Gin + PostgreSQL | Lambda + DynamoDB |
| Notificaciones | Consume eventos, genera alertas | Python/FastAPI + PostgreSQL | Lambda consumer + DynamoDB |
| Gestión de Agentes | Agentes, disponibilidad, skills | Node.js/Express + PostgreSQL | Lambda + DynamoDB |

## API Endpoints

```bash
# Customers
GET    /api/v1/customers              # Listar clientes
POST   /api/v1/customers              # Crear cliente
GET    /api/v1/customers/:id          # Obtener cliente
PUT    /api/v1/customers/:id          # Actualizar cliente
DELETE /api/v1/customers/:id          # Eliminar cliente (soft delete)

# Tickets
GET    /api/v1/tickets                # Listar tickets (?status=OPEN)
POST   /api/v1/tickets                # Crear ticket
GET    /api/v1/tickets/:id            # Obtener ticket
PUT    /api/v1/tickets/:id/assign     # Asignar agente
PUT    /api/v1/tickets/:id/start      # Iniciar progreso
PUT    /api/v1/tickets/:id/resolve    # Resolver ticket
PUT    /api/v1/tickets/:id/close      # Cerrar ticket
PUT    /api/v1/tickets/:id/reopen     # Reabrir ticket

# Knowledge Base
GET    /api/v1/articles               # Listar artículos (?category_id=...)
POST   /api/v1/articles               # Crear artículo
GET    /api/v1/articles/:id           # Obtener artículo
PUT    /api/v1/articles/:id           # Actualizar artículo
GET    /api/v1/categories             # Listar categorías
POST   /api/v1/categories             # Crear categoría

# Notifications
GET    /api/v1/notifications          # Listar notificaciones (?recipient_id=...)
GET    /api/v1/notifications/:id      # Obtener notificación

# Agents
GET    /api/v1/agents                 # Listar agentes
POST   /api/v1/agents                 # Crear agente
GET    /api/v1/agents/:id             # Obtener agente
PUT    /api/v1/agents/:id             # Actualizar agente
PUT    /api/v1/agents/:id/status      # Cambiar estado (ONLINE/OFFLINE/BUSY)
GET    /api/v1/agents/available/next  # Siguiente agente disponible (Strategy)
```

## Flujo de Eventos

```
[Cliente crea ticket]
    │
    ▼
tickets Lambda → publica: ticket.created → SNS Topic
    │
    ├──▶ SQS → notifications-consumer → crea notificación (Factory pattern)
    │
    └──▶ (API call) → agents Lambda /available/next → selecciona agente (Strategy)
              │
              ▼
         tickets Lambda ← PUT /tickets/:id/assign
              │
              ▼
         publica: ticket.assigned → SNS Topic
              │
              ├──▶ SQS → notifications-consumer → notifica al cliente
              │
              └──▶ SQS → agents-consumer → incrementa active_tickets_count
                                            (atomic counter, auto-BUSY)
```
