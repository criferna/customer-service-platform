# Laboratorio de Microservicios — Actividades

**Plataforma:** Customer Service Platform  
**Repositorio:** github.com/criferna/customer-service-platform  
**Fecha:** Abril 2026

---

## Tabla de Contenidos

1. [Visión General](#1-visión-general)
2. [Actividad 1: Arquitectura de Microservicios](#actividad-1-arquitectura-de-microservicios)
3. [Actividad 2: Domain-Driven Design (DDD)](#actividad-2-domain-driven-design-ddd)
4. [Actividad 3: Database per Service](#actividad-3-database-per-service)
5. [Actividad 4: Event-Driven Architecture](#actividad-4-event-driven-architecture)
6. [Actividad 5: API Gateway](#actividad-5-api-gateway)
7. [Actividad 6: Contenedores y Orquestación](#actividad-6-contenedores-y-orquestación)
8. [Actividad 7: Independencia Tecnológica](#actividad-7-independencia-tecnológica)
9. [Actividad 8: Observabilidad](#actividad-8-observabilidad)
10. [Actividad 9: CI/CD y DevOps](#actividad-9-cicd-y-devops)
11. [Actividad 10: Patrones de Diseño](#actividad-10-patrones-de-diseño)
12. [Actividad 11: Migración Docker a AWS Serverless](#actividad-11-migración-docker-a-aws-serverless)
13. [Actividad 12: Infrastructure as Code (Terraform)](#actividad-12-infrastructure-as-code-terraform)
14. [Resumen de Arquitectura](#resumen-de-arquitectura)

---

## 1. Visión General

### Qué es esta plataforma

Una plataforma de servicio al cliente que gestiona clientes, tickets de soporte, agentes, base de conocimiento y notificaciones. Implementada dos veces con tecnologías diferentes para demostrar principios de microservicios:

| Aspecto | Docker (On-Premise) | AWS (Serverless) |
|---|---|---|
| Compute | 5 contenedores Docker | 8 Lambda functions |
| API Gateway | Kong | Amazon API Gateway |
| Base de datos | 5 instancias PostgreSQL | 6 tablas DynamoDB |
| Event Bus | RabbitMQ | SNS + SQS |
| Observabilidad | Prometheus + Grafana | CloudWatch |
| CI/CD | Jenkins (Jenkinsfile) | GitHub Actions |
| IaC | Docker Compose | Terraform |

### Estructura del repositorio

```
customer-service-platform/
├── services/                    # 5 microservicios Docker
│   ├── customers-service/       #   Python + FastAPI
│   ├── tickets-service/         #   Node.js + Express
│   ├── agents-service/          #   Node.js + Express
│   ├── notifications-service/   #   Python + FastAPI
│   └── knowledge-service/       #   Go + Gin
├── infrastructure/              # Docker Compose + Kong + RabbitMQ + Monitoring
├── aws-lambdas/                 # 8 Lambda handlers + shared layer
│   ├── shared/                  #   5 patrones de diseño
│   └── functions/               #   5 APIs + 3 consumers
├── terraform/                   # IaC para AWS
├── .github/workflows/           # GitHub Actions CI/CD
├── scripts/                     # Deploy + health checks
└── Jenkinsfile                  # Pipeline Jenkins
```

---

## Actividad 1: Arquitectura de Microservicios

### Teoría

Un microservicio es una unidad de software **independiente** que:
- Tiene una **responsabilidad única** (alta cohesión)
- Se despliega de forma **independiente**
- Se comunica con otros servicios a través de **interfaces definidas** (API REST, eventos)
- Mantiene su **propia base de datos** (Database per Service)

**Ventajas sobre monolitos:**
- Escalabilidad selectiva (escalar solo lo que se necesita)
- Resiliencia (fallo de un servicio no tumba toda la plataforma)
- Equipos autónomos (cada equipo es dueño de su servicio)
- Libertad tecnológica (cada servicio elige su stack)

**Desventajas:**
- Complejidad operacional (más servicios = más cosas que monitorear)
- Consistencia eventual (no hay transacciones distribuidas simples)
- Latencia de red (llamadas entre servicios vs llamadas en memoria)

### Práctica

Se implementaron **5 microservicios** independientes:

| Servicio | Puerto | Responsabilidad |
|---|---|---|
| `customers-service` | 8001 | CRUD de clientes, soft delete |
| `tickets-service` | 8002 | Workflow de tickets, State Machine |
| `agents-service` | 8003 | Gestión de agentes, disponibilidad |
| `notifications-service` | 8004 | Consume eventos, genera notificaciones |
| `knowledge-service` | 8005 | Artículos y categorías de ayuda |

**Verificación práctica:**
```bash
# Cada servicio corre de forma independiente
docker compose ps

# Escalar un servicio sin afectar los demás
docker compose up -d --scale tickets-service=3

# Detener un servicio — los otros siguen operando
docker compose stop notifications-service
curl http://localhost:8000/api/v1/customers  # sigue funcionando
```

---

## Actividad 2: Domain-Driven Design (DDD)

### Teoría

DDD organiza el software alrededor del **dominio del negocio**, no de la tecnología. Conceptos clave:

| Concepto | Definición | Ejemplo en el lab |
|---|---|---|
| **Bounded Context** | Límite explícito donde un modelo de dominio aplica | Gestión de Clientes, Gestión de Tickets |
| **Aggregate Root** | Entidad principal que garantiza consistencia | Customer, Ticket, Agent |
| **Value Object** | Objeto definido por su valor, inmutable | email, phone, status |
| **Domain Event** | Registro de algo que sucedió en el dominio | `ticket.created`, `customer.updated` |
| **Repository** | Abstracción para persistencia del aggregate | PostgreSQL adapter, DynamoDB adapter |
| **Ubiquitous Language** | Lenguaje compartido entre negocio y código | "crear ticket", "asignar agente", "resolver" |

### Práctica

Cada servicio sigue la estructura DDD por capas:

```
service/src/
├── domain/              # Capa de Dominio (reglas de negocio puras)
│   ├── entities/        #   Entidades con identidad (Customer, Ticket)
│   ├── events/          #   Eventos de dominio inmutables
│   └── value_objects/   #   Objetos de valor (email, status)
├── application/         # Capa de Aplicación (casos de uso)
│   ├── use_cases/       #   Orquesta la lógica del dominio
│   └── dto/             #   Data Transfer Objects
├── infrastructure/      # Capa de Infraestructura (adapters)
│   ├── database/        #   Conexión y modelos de persistencia
│   ├── messaging/       #   Publisher/Consumer de eventos
│   └── repositories/    #   Implementaciones de Repository
└── presentation/        # Capa de Presentación (API)
    ├── routes/          #   Endpoints HTTP
    └── middleware/      #   Correlation ID, logging, auth
```

**5 Bounded Contexts identificados:**

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Gestión Clientes │  │ Gestión Tickets  │  │ Gestión Agentes  │
│                  │  │                  │  │                  │
│ Aggregate:       │  │ Aggregate:       │  │ Aggregate:       │
│   Customer       │  │   Ticket         │  │   Agent          │
│                  │  │                  │  │                  │
│ Events:          │  │ Events:          │  │ Events:          │
│ customer.created │  │ ticket.created   │  │ agent.updated    │
│ customer.updated │  │ ticket.assigned  │  │ agent.status_    │
│ customer.deleted │  │ ticket.resolved  │  │   changed        │
└──────────────────┘  └──────────────────┘  └──────────────────┘

┌──────────────────┐  ┌──────────────────┐
│ Notificaciones   │  │ Base Conocimient.│
│                  │  │                  │
│ Aggregate:       │  │ Aggregates:      │
│   Notification   │  │   Category       │
│                  │  │   Article        │
│ Consume:         │  │                  │
│ ticket.*         │  │ Events:          │
│ customer.*       │  │ article.created  │
└──────────────────┘  └──────────────────┘
```

**Comunicación entre contextos:**
- Cada contexto tiene su propia base de datos (no comparten tablas)
- Se comunican **solo via eventos** (nunca llamadas directas entre servicios)
- Consistencia eventual: los datos se sincronizan asincrónicamente

---

## Actividad 3: Database per Service

### Teoría

Cada microservicio posee su propia base de datos. Ningún servicio accede directamente a la base de datos de otro. Esto garantiza:

- **Autonomía**: un servicio puede cambiar su schema sin afectar a otros
- **Aislamiento de fallos**: si una BD cae, solo afecta a su servicio
- **Libertad tecnológica**: cada servicio puede usar la BD que mejor le convenga

**Trade-off principal**: no se pueden hacer JOINs entre tablas de diferentes servicios. Se resuelve con:
- **Datos desnormalizados** (copiar datos relevantes entre servicios)
- **Eventos de dominio** (propagar cambios asincrónicamente)

### Práctica — Docker (PostgreSQL)

5 instancias PostgreSQL aisladas:

```yaml
# infrastructure/docker-compose.yml
cs-customers-db:
  image: postgres:16-alpine
  environment:
    POSTGRES_DB: customers_db
  volumes:
    - customers-db-data:/var/lib/postgresql/data

cs-tickets-db:
  image: postgres:16-alpine
  environment:
    POSTGRES_DB: tickets_db
  volumes:
    - tickets-db-data:/var/lib/postgresql/data

# ... 3 más para agents, notifications, knowledge
```

### Práctica — AWS (DynamoDB)

6 tablas DynamoDB con Global Secondary Indexes (GSIs):

| Tabla | PK | GSIs | Servicio |
|---|---|---|---|
| `lab-ms-customers` | `id` | `email-index` | customers |
| `lab-ms-tickets` | `id` | `status-index`, `customer-index` | tickets |
| `lab-ms-agents` | `id` | `status-index` | agents |
| `lab-ms-notifications` | `id` | `recipient-index` | notifications |
| `lab-ms-knowledge-categories` | `id` | — | knowledge |
| `lab-ms-knowledge-articles` | `id` | `category-index` | knowledge |

**Datos desnormalizados en acción:**
```
Ticket almacena:
  - customer_id (referencia)
  - customer_name (copia desnormalizada)
  - customer_email (copia desnormalizada)
  - assigned_agent_name (copia desnormalizada)

Cuando customer.updated → tickets-consumer actualiza las copias
Cuando agent.updated → tickets-consumer actualiza assigned_agent_name
```

---

## Actividad 4: Event-Driven Architecture

### Teoría

En vez de que los servicios se llamen directamente (acoplamiento fuerte), publican **eventos** que otros servicios consumen (acoplamiento débil).

**Componentes:**
- **Producer/Publisher**: servicio que emite un evento cuando algo ocurre
- **Event Bus/Broker**: infraestructura que distribuye los eventos
- **Consumer/Subscriber**: servicio que reacciona al evento

**Beneficios:**
- Desacoplamiento: el producer no sabe ni le importa quién consume
- Escalabilidad: agregar consumers sin modificar el producer
- Resiliencia: si un consumer falla, el evento queda en la cola para reintento

### Práctica — Docker (RabbitMQ)

```
                    ┌─────────────────────────────┐
                    │   RabbitMQ (Event Bus)       │
                    │                             │
                    │   Exchange: customer_service │
                    │   Type: topic               │
                    │                             │
tickets-service ──▶ │   Routing Keys:             │
                    │     ticket.created    ──────▶ notifications queue
                    │     ticket.assigned   ──────▶ notifications queue
                    │     ticket.resolved   ──────▶ notifications queue
                    │     ticket.resolved   ──────▶ agents queue
                    └─────────────────────────────┘
```

**Configuración (`infrastructure/rabbitmq/definitions.json`):**
- Exchange tipo `topic` con routing keys
- Queues con bindings por servicio
- Dead Letter Exchange para mensajes fallidos
- Usuario `cs_platform` con permisos sobre vhost `customer_service`

### Práctica — AWS (SNS + SQS)

```
                    ┌──────────────────────────────────┐
                    │  SNS Topic: lab-ms-domain-events │
                    │  (Observer Pattern)              │
                    │                                  │
Lambda publish() ──▶│  Filter Policies:                │
                    │    ticket.* ─────▶ SQS: notifications-ticket-events
                    │    ticket.* ─────▶ SQS: agents-ticket-events
                    │    customer.* ───▶ SQS: tickets-customer-events
                    │    agent.* ──────▶ SQS: tickets-customer-events
                    └──────────────────────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │  Dead Letter Queues (DLQ)  │
                    │  Retención: 14 días        │
                    │  maxReceiveCount: 3         │
                    └───────────────────────────┘
```

**SNS Message Attributes** permiten filtrado (equivalente a routing keys de RabbitMQ):
```python
# aws-lambdas/shared/observer.py — DomainEventPublisher
message_attributes = {
    "event_type": {
        "DataType": "String",
        "StringValue": event_type,  # ej: "ticket.created"
    },
}
```

### Flujo de eventos completo

```
1. Cliente crea ticket via API
   └─▶ tickets Lambda publica: ticket.created → SNS

2. SNS distribuye a 3 colas SQS (fan-out):
   ├─▶ notifications-consumer: crea notificación "Tu ticket fue recibido"
   ├─▶ agents-consumer: (no aplica para created, ignora)
   └─▶ tickets-consumer: (no aplica, ignora)

3. Agente es asignado al ticket
   └─▶ tickets Lambda publica: ticket.assigned → SNS
       ├─▶ notifications-consumer: crea notificación "Tu ticket fue asignado"
       └─▶ agents-consumer: incrementa active_tickets_count del agente
                            si count >= max_tickets → status = BUSY

4. Ticket es resuelto
   └─▶ tickets Lambda publica: ticket.resolved → SNS
       ├─▶ notifications-consumer: crea notificación "Tu ticket fue resuelto"
       └─▶ agents-consumer: decrementa active_tickets_count
                            si estaba BUSY y ahora tiene capacidad → ONLINE
```

---

## Actividad 5: API Gateway

### Teoría

El API Gateway es el **punto de entrada único** para todos los clientes. Funciones:

- **Routing**: dirige cada request al servicio correcto
- **CORS**: headers de Cross-Origin Resource Sharing
- **Rate Limiting**: protección contra abuso
- **Autenticación**: validación centralizada de tokens (en producción)
- **Logging**: registro centralizado de todos los requests

Sin API Gateway, los clientes necesitarían conocer la IP y puerto de cada servicio individualmente.

### Práctica — Docker (Kong)

```yaml
# infrastructure/kong/kong.yml
services:
  - name: customers-service
    url: http://customers-service:8001
    routes:
      - name: customers-route
        paths: ["/api/v1/customers"]

  - name: tickets-service
    url: http://tickets-service:8002
    routes:
      - name: tickets-route
        paths: ["/api/v1/tickets"]

# ... 3 más para agents, notifications, knowledge
```

Acceso unificado: `http://192.168.0.125:8000/api/v1/*`

### Práctica — AWS (API Gateway)

```hcl
# terraform/api_gateway.tf
resource "aws_api_gateway_rest_api" "main" {
  name = "lab-ms-api"
}

# Cada ruta apunta a su Lambda via AWS_PROXY integration:
# /api/v1/customers     → lab-ms-customers Lambda
# /api/v1/tickets       → lab-ms-tickets Lambda
# /api/v1/agents        → lab-ms-agents Lambda
# /api/v1/notifications → lab-ms-notifications Lambda
# /api/v1/categories    → lab-ms-knowledge Lambda
# /api/v1/articles      → lab-ms-knowledge Lambda
```

Acceso unificado: `https://aonn2v35n0.execute-api.us-east-2.amazonaws.com/dev/api/v1/*`

### 36 endpoints disponibles

```bash
# Customers (5 endpoints)
GET    /api/v1/customers              # Listar
POST   /api/v1/customers              # Crear
GET    /api/v1/customers/{id}         # Obtener
PUT    /api/v1/customers/{id}         # Actualizar
DELETE /api/v1/customers/{id}         # Soft delete

# Tickets (8 endpoints)
GET    /api/v1/tickets                # Listar (?status=OPEN)
POST   /api/v1/tickets                # Crear
GET    /api/v1/tickets/{id}           # Obtener
PUT    /api/v1/tickets/{id}/assign    # Asignar agente
PUT    /api/v1/tickets/{id}/start     # Iniciar progreso
PUT    /api/v1/tickets/{id}/resolve   # Resolver
PUT    /api/v1/tickets/{id}/close     # Cerrar
PUT    /api/v1/tickets/{id}/reopen    # Reabrir

# Agents (6 endpoints)
GET    /api/v1/agents                 # Listar
POST   /api/v1/agents                 # Crear
GET    /api/v1/agents/{id}            # Obtener
PUT    /api/v1/agents/{id}            # Actualizar
PUT    /api/v1/agents/{id}/status     # Cambiar estado
GET    /api/v1/agents/available/next  # Siguiente disponible (Strategy)

# Knowledge (6 endpoints)
GET    /api/v1/categories             # Listar categorías
POST   /api/v1/categories             # Crear categoría
GET    /api/v1/articles               # Listar artículos (?category_id=)
POST   /api/v1/articles               # Crear artículo
GET    /api/v1/articles/{id}          # Obtener artículo
PUT    /api/v1/articles/{id}          # Actualizar artículo

# Notifications (2 endpoints)
GET    /api/v1/notifications          # Listar (?recipient_id=)
GET    /api/v1/notifications/{id}     # Obtener
```

---

## Actividad 6: Contenedores y Orquestación

### Teoría

**Docker** empaqueta una aplicación con todas sus dependencias en una imagen portable. Garantiza que el software corre exactamente igual en desarrollo, staging y producción.

**Docker Compose** orquesta múltiples contenedores como una unidad:
- Define servicios, redes, y volúmenes en un archivo YAML
- Gestiona dependencias entre servicios (`depends_on`)
- Health checks automáticos
- Restart policies para auto-recuperación

**Multi-stage builds** reducen el tamaño de la imagen final separando la fase de compilación de la fase de ejecución.

### Práctica

**Docker Compose** orquesta 13+ contenedores:

```yaml
# infrastructure/docker-compose.yml — 13 servicios
services:
  # --- 5 Microservicios ---
  customers-service:     # Python + FastAPI
  tickets-service:       # Node.js + Express
  agents-service:        # Node.js + Express
  notifications-service: # Python + FastAPI
  knowledge-service:     # Go + Gin

  # --- 5 Bases de Datos ---
  cs-customers-db:       # PostgreSQL 16
  cs-tickets-db:         # PostgreSQL 16
  cs-agents-db:          # PostgreSQL 16
  cs-notifications-db:   # PostgreSQL 16
  cs-knowledge-db:       # PostgreSQL 16

  # --- Infraestructura ---
  cs-kong:               # API Gateway
  cs-rabbitmq:           # Event Bus
  cs-jenkins:            # CI/CD
```

**Ejemplo de multi-stage build (Go):**
```dockerfile
# services/knowledge-service/Dockerfile
FROM golang:1.21-alpine AS builder       # Stage 1: compilar
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o server ./cmd/main.go

FROM alpine:3.19                          # Stage 2: imagen final
COPY --from=builder /app/server /server
EXPOSE 8005
CMD ["/server"]
# Resultado: imagen de ~15MB vs ~1GB con toda la toolchain
```

**Health checks y resiliencia:**
```yaml
customers-service:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
    interval: 30s
    timeout: 10s
    retries: 3
  restart: unless-stopped
  depends_on:
    cs-customers-db:
      condition: service_healthy
```

---

## Actividad 7: Independencia Tecnológica

### Teoría

Uno de los beneficios clave de microservicios es la **libertad de elegir la tecnología** más apropiada para cada servicio. El contrato entre servicios es la API (REST + eventos), no la implementación interna.

Esto permite:
- Usar el mejor lenguaje/framework para cada problema
- Migrar servicios individualmente sin reescribir todo
- Experimentar con nuevas tecnologías de forma aislada

### Práctica

El mismo sistema se implementó con **3 tecnologías en Docker** y luego se migró completo a **Python en AWS Lambda**:

| Bounded Context | Docker | AWS Lambda |
|---|---|---|
| Customers | **Python 3** + FastAPI + SQLAlchemy | **Python 3.12** + boto3 |
| Tickets | **Node.js** + Express + Sequelize | **Python 3.12** + boto3 |
| Agents | **Node.js** + Express + Sequelize | **Python 3.12** + boto3 |
| Notifications | **Python 3** + FastAPI + SQLAlchemy | **Python 3.12** + boto3 |
| Knowledge | **Go** + Gin + GORM | **Python 3.12** + boto3 |

**Punto clave**: el Bounded Context de Knowledge se implementó en Go (Docker) y luego en Python (AWS), exponiendo exactamente la misma API REST. Esto demuestra que la tecnología es un **detalle de implementación**, no una decisión arquitectónica del dominio.

```
Misma API, diferente tecnología:

GET /api/v1/articles          # Docker: Go + Gin + PostgreSQL
GET /api/v1/articles          # AWS: Python 3.12 + DynamoDB

Ambos retornan el mismo JSON, mismos campos, mismo contrato.
```

---

## Actividad 8: Observabilidad

### Teoría

Observabilidad = capacidad de entender el estado interno del sistema a partir de sus salidas. Tres pilares:

| Pilar | Qué es | Herramienta Docker | Herramienta AWS |
|---|---|---|---|
| **Logs** | Registro de eventos textuales | JSON logs + Docker logs | CloudWatch Logs |
| **Métricas** | Datos numéricos agregados | Prometheus + Grafana | CloudWatch Metrics |
| **Tracing** | Seguimiento de requests entre servicios | Correlation ID (X-Correlation-ID) | Correlation ID |

### Práctica — Correlation ID (Tracing Distribuido)

Cada request recibe un ID único que se propaga a través de todos los servicios involucrados. Permite rastrear un request completo desde el API Gateway hasta el último consumer.

```python
# aws-lambdas/shared/decorator.py — with_correlation_id
def wrapper(event, context):
    headers = event.get("headers") or {}
    correlation_id = None
    for key, value in headers.items():
        if key.lower() == "x-correlation-id":
            correlation_id = value
            break
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    event["correlation_id"] = correlation_id
    response = handler(event, context)
    response["headers"]["X-Correlation-ID"] = correlation_id
    return response
```

**Logging estructurado (JSON):**
```json
{
  "timestamp": "2026-04-23T23:32:35Z",
  "service": "tickets-service",
  "level": "INFO",
  "message": "Incoming POST /api/v1/tickets",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "method": "POST",
  "path": "/api/v1/tickets",
  "duration_ms": 45.2
}
```

### Práctica — Docker (Prometheus + Grafana)

```yaml
# infrastructure/docker-compose.yml
prometheus:
  image: prom/prometheus:v2.53.0
  volumes:
    - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana:11.1.0
  ports:
    - "3005:3000"
```

### Práctica — AWS (CloudWatch)

```hcl
# terraform/lambda.tf — Log groups con retención de 7 días
resource "aws_cloudwatch_log_group" "customers" {
  name              = "/aws/lambda/lab-ms-customers"
  retention_in_days = 7
}
```

9 log groups creados: 8 para Lambda functions + 1 para API Gateway.

---

## Actividad 9: CI/CD y DevOps

### Teoría

**CI (Continuous Integration)**: cada cambio de código se valida automáticamente (lint, tests, build).

**CD (Continuous Delivery/Deployment)**: el código validado se despliega automáticamente al ambiente productivo.

**Pipeline as Code**: la definición del pipeline está versionada en el repositorio (Jenkinsfile, YAML de GitHub Actions).

### Práctica — Docker (Jenkins)

```groovy
// Jenkinsfile — 5 stages
pipeline {
    agent any
    stages {
        stage('Checkout')  { /* git pull */ }
        stage('Build')     { /* docker compose build */ }
        stage('Test')      { /* docker compose run tests */ }
        stage('Deploy')    { /* docker compose up -d */ }
        stage('Verify')    { /* health checks a cada servicio */ }
    }
}
```

### Práctica — AWS (GitHub Actions)

**Workflow 1: Infrastructure (`infra.yml`)**
```
Push a terraform/ o aws-lambdas/
  │
  ├─▶ Validate: terraform fmt + init + validate
  │
  ├─▶ [Si es PR] Plan: terraform plan → comentario en PR
  │
  └─▶ [Si es merge a main] Apply: terraform apply -auto-approve
```

**Workflow 2: Deploy Lambdas (`deploy.yml`)**
```
Push a aws-lambdas/
  │
  ├─▶ Lint: flake8 sobre código Python
  │
  └─▶ [Merge a main] Deploy:
        1. Package shared layer → publish Lambda Layer
        2. Package cada handler → update-function-code
        3. Verify: confirmar estado de cada Lambda
```

**Secrets requeridos en GitHub:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

---

## Actividad 10: Patrones de Diseño

### Teoría

Los patrones de diseño son soluciones reutilizables a problemas comunes de software. Se clasifican en:

| Categoría | Propósito | Patrones en el lab |
|---|---|---|
| **Creacionales** | Cómo se crean los objetos | Singleton, Factory |
| **Estructurales** | Cómo se componen los objetos | Decorator |
| **Comportamiento** | Cómo interactúan los objetos | Observer, Strategy |

### Patrón 1: Singleton (Creacional)

**Problema**: crear un cliente DynamoDB o SNS en cada invocación Lambda es costoso.

**Solución**: garantizar una única instancia por contenedor Lambda (reutilizada en warm starts).

```python
# aws-lambdas/shared/singleton.py
class DynamoDBClient:
    _instance = None
    _resource = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._resource = boto3.resource("dynamodb",
                region_name=os.environ.get("AWS_REGION", "us-east-2"))
        return cls._instance

    def table(self, table_name: str):
        return self._resource.Table(table_name)

# Uso: siempre retorna la misma instancia
db = DynamoDBClient()  # primera vez: crea conexión
db = DynamoDBClient()  # segunda vez: reutiliza la existente
```

**Cuándo usarlo**: clientes de BD, HTTP clients, loggers, caches, configuración.

### Patrón 2: Factory (Creacional)

**Problema**: el servicio de notificaciones debe enviar por diferentes canales (internal, email, SNS) según el ambiente.

**Solución**: un Factory que crea el notificador correcto según configuración, sin que el consumer sepa cuál se usa.

```python
# aws-lambdas/shared/factory.py
class NotificationFactory:
    _notifiers = {
        "INTERNAL": InternalNotifier,   # Solo log (desarrollo)
        "EMAIL": EmailNotifier,         # Amazon SES (producción)
        "SNS": SnsNotifier,             # SNS topic (fan-out)
    }

    @classmethod
    def create(cls, channel=None) -> Notifier:
        channel = channel or os.environ.get("NOTIFICATION_CHANNEL", "INTERNAL")
        notifier_class = cls._notifiers.get(channel.upper())
        return notifier_class()

# Uso en el consumer:
notifier = NotificationFactory.create()  # lee NOTIFICATION_CHANNEL del env
notifier.send("maria@test.cl", "Ticket creado", "Tu ticket fue recibido")
# No importa si es Internal, Email o SNS — la interfaz es la misma
```

**Cuándo usarlo**: procesadores de pagos, adaptadores de BD, parsers de archivos.

### Patrón 3: Decorator (Estructural)

**Problema**: todos los Lambda handlers necesitan error handling, logging, correlation ID y JSON parsing. Repetir esto en cada handler viola DRY.

**Solución**: decoradores que envuelven al handler agregando funcionalidad sin modificarlo.

```python
# aws-lambdas/shared/decorator.py
@lambda_handler()
def handler(event, context):
    # Este handler YA tiene:
    # 1. JSON body parseado en event["parsed_body"]
    # 2. Errores capturados (ValueError→400, KeyError→404, Exception→500)
    # 3. Correlation ID en event["correlation_id"]
    # 4. Logging de entrada/salida con timing
    return response(200, {"data": "hello"})

# Equivale a:
# handler = with_logging(
#     with_correlation_id(
#         with_error_handler(
#             with_json_body(handler))))
```

**Capas del decorator stack:**

```
Request entrante
  │
  ▼ with_logging ──── log: "Incoming POST /api/v1/tickets"
  │
  ▼ with_correlation_id ──── genera/propaga X-Correlation-ID
  │
  ▼ with_error_handler ──── try/catch → 400, 404, 500
  │
  ▼ with_json_body ──── parsea body JSON → event["parsed_body"]
  │
  ▼ handler(event, context) ──── lógica de negocio
  │
  ▲ with_logging ──── log: "Completed POST /api/v1/tickets 201 45.2ms"
```

**Cuándo usarlo**: middleware de APIs, retry logic, circuit breaker, caching, auth.

### Patrón 4: Observer (Comportamiento)

**Problema**: cuando se crea un ticket, múltiples servicios deben reaccionar (notificaciones, agentes) sin que tickets-service los conozca.

**Solución**: el Observer define una dependencia uno-a-muchos. El Subject (SNS) notifica a todos los Observers (SQS queues) automáticamente.

```python
# aws-lambdas/shared/observer.py
class DomainEventPublisher:
    def publish(self, event_type, aggregate_id, payload, correlation_id=None):
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,        # "ticket.created"
            "aggregate_id": str(aggregate_id),
            "correlation_id": correlation_id,
            "payload": payload,
        }
        self.sns.publish(
            topic_arn=self.topic_arn,
            message=json.dumps(event),
            message_attributes={
                "event_type": {"DataType": "String", "StringValue": event_type}
            },
        )

# Uso: el producer no sabe quién consume
publisher.publish("ticket.created", ticket_id, ticket_data)
# SNS distribuye automáticamente a:
#   → notifications-consumer (crea notificación)
#   → agents-consumer (actualiza carga)
#   → tickets-consumer (no aplica, ignora)
```

**Mapeo Docker → AWS:**
- RabbitMQ Exchange = SNS Topic (Subject)
- RabbitMQ Queues = SQS Queues (Observers)
- Routing Keys = SNS Filter Policies

**Cuándo usarlo**: event-driven architecture, cache invalidation, audit logging.

### Patrón 5: Strategy (Comportamiento)

**Problema**: hay múltiples algoritmos válidos para asignar un agente a un ticket. El algoritmo debe poder cambiarse sin modificar código.

**Solución**: encapsular cada algoritmo en una clase, seleccionar por configuración en runtime.

```python
# aws-lambdas/shared/strategy.py
class LeastLoadedStrategy(AssignmentStrategy):
    """Asigna al agente con MENOS tickets activos."""
    def select_agent(self, agents, ticket):
        return min(agents, key=lambda a: a.get("active_tickets_count", 0))

class RoundRobinStrategy(AssignmentStrategy):
    """Asigna de forma ROTATORIA (counter + módulo)."""
    _counter = 0
    def select_agent(self, agents, ticket):
        index = RoundRobinStrategy._counter % len(agents)
        RoundRobinStrategy._counter += 1
        return agents[index]

class SkillBasedStrategy(AssignmentStrategy):
    """Asigna al agente que tenga el SKILL del ticket."""
    def select_agent(self, agents, ticket):
        category = ticket.get("category", "").lower()
        skilled = [a for a in agents
                   if category in [s.lower() for s in a.get("skills", [])]]
        if skilled:
            return min(skilled, key=lambda a: a.get("active_tickets_count", 0))
        return min(agents, key=lambda a: a.get("active_tickets_count", 0))

# Selección via variable de entorno
ctx = AgentAssignmentContext()  # lee ASSIGNMENT_STRATEGY del env
agent = ctx.assign(available_agents, ticket)
# Cambiar a ROUND_ROBIN o SKILL_BASED sin tocar código
```

**Cuándo usarlo**: pricing, cache eviction (LRU/LFU), routing, validación, ranking.

---

## Actividad 11: Migración Docker a AWS Serverless

### Teoría

**Serverless** = el proveedor cloud gestiona los servidores. El desarrollador solo escribe código de negocio:
- **No hay servidores** que administrar, parchear o escalar
- **Pay-per-use**: cobro por invocación, no por tiempo encendido
- **Auto-scaling**: de 0 a miles de invocaciones concurrentes automáticamente
- **Free Tier**: Lambda ofrece 1M invocaciones/mes gratis

### Práctica — Mapeo de componentes

| Docker (On-Premise) | AWS (Serverless) | Razón del cambio |
|---|---|---|
| 5 contenedores Docker | 8 Lambda functions | Sin servidores, auto-scaling |
| Kong (API Gateway) | Amazon API Gateway | Managed, HTTPS gratis |
| 5 PostgreSQL | 6 DynamoDB tables | Serverless, pay-per-request |
| RabbitMQ | SNS + SQS | Managed, sin mantención |
| Prometheus + Grafana | CloudWatch | Integrado, sin infraestructura |
| Jenkins | GitHub Actions | Sin servidor Jenkins |
| Docker Compose | Terraform | Reproducible, versionable |
| docker-compose.yml | *.tf files | Infrastructure as Code |

### Práctica — State Machine (tickets)

El workflow de tickets implementa una máquina de estados que se preservó en la migración:

```
                    ┌────────┐
                    │  OPEN  │ ◄──── Ticket creado
                    └───┬────┘
                        │ assign
                    ┌───▼──────┐
             ┌─────▶│ ASSIGNED │◄─────────────────┐
             │      └───┬──────┘                   │
             │          │ start                    │
             │      ┌───▼────────┐                 │
             │      │IN_PROGRESS │                 │
             │      └───┬────────┘                 │
             │          │ resolve                  │
         reopen     ┌───▼──────┐              assign
             │      │ RESOLVED │                   │
             │      └─┬──────┬─┘                   │
             │        │      │                     │
             │  close │      │ reopen              │
             │  ┌─────▼─┐  ┌▼─────────┐           │
             │  │CLOSED │  │ REOPENED  ├───────────┘
             │  └───────┘  └──────────┘
             │  (terminal)
             └─────────────────────────────────────
```

```python
# aws-lambdas/functions/tickets/handler.py
VALID_TRANSITIONS = {
    "OPEN":        {"ASSIGNED"},
    "ASSIGNED":    {"IN_PROGRESS", "OPEN"},
    "IN_PROGRESS": {"RESOLVED", "ASSIGNED"},
    "RESOLVED":    {"CLOSED", "REOPENED"},
    "CLOSED":      set(),  # terminal
    "REOPENED":    {"ASSIGNED"},
}
```

---

## Actividad 12: Infrastructure as Code (Terraform)

### Teoría

**Infrastructure as Code (IaC)** = definir infraestructura en archivos de código versionables, revisables y reproducibles. Beneficios:

- **Reproducibilidad**: `terraform apply` crea el mismo ambiente siempre
- **Versionamiento**: cambios en infraestructura pasan por code review
- **Automatización**: CI/CD aplica cambios automáticamente
- **Documentación viva**: el código ES la documentación de la infra
- **Estado**: Terraform mantiene un estado que sabe qué existe y qué falta

### Práctica

9 archivos Terraform definen toda la infraestructura AWS:

```
terraform/
├── versions.tf       # Provider AWS + backend S3
├── variables.tf      # 8 variables configurables
├── dynamodb.tf       # 6 tablas con GSIs
├── sns_sqs.tf        # 1 SNS + 3 SQS + 3 DLQs + filter policies
├── iam.tf            # 8 roles + 10 policies (least privilege)
├── lambda.tf         # 8 functions + layer + event source mappings
├── api_gateway.tf    # REST API + resources + methods + integrations
└── outputs.tf        # API URL, ARNs, nombres
```

**Ejemplo — DynamoDB con GSI:**
```hcl
# terraform/dynamodb.tf
resource "aws_dynamodb_table" "tickets" {
  name         = "lab-ms-tickets"
  billing_mode = "PAY_PER_REQUEST"  # Free Tier friendly
  hash_key     = "id"

  attribute { name = "id"     type = "S" }
  attribute { name = "status" type = "S" }

  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    projection_type = "ALL"
  }
}
```

**Ejemplo — Lambda con Layer:**
```hcl
# terraform/lambda.tf
resource "aws_lambda_function" "tickets" {
  function_name = "lab-ms-tickets"
  handler       = "handler.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 128
  role          = aws_iam_role.tickets_lambda.arn
  layers        = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = {
      DOMAIN_EVENTS_TOPIC_ARN = aws_sns_topic.domain_events.arn
      SERVICE_NAME            = "tickets-service"
    }
  }
}
```

**Estado remoto (compartido en CI/CD):**
```hcl
# terraform/versions.tf
backend "s3" {
  bucket         = "lab-ms-terraform-state"
  key            = "customer-service-platform/terraform.tfstate"
  region         = "us-east-2"
  dynamodb_table = "lab-ms-terraform-locks"  # locking para concurrencia
  encrypt        = true
}
```

---

## Resumen de Arquitectura

### Inventario de recursos AWS en producción

| Servicio AWS | Recursos | Cantidad |
|---|---|---|
| Lambda | 5 APIs + 3 consumers + 1 layer | 9 |
| DynamoDB | 6 tablas de negocio + 1 terraform locks | 7 |
| API Gateway | REST API `lab-ms-api` | 1 |
| SNS | Topic `lab-ms-domain-events` | 1 |
| SQS | 3 queues + 3 DLQs | 6 |
| CloudWatch | 9 log groups (retención 7 días) | 9 |
| IAM | 9 roles + 10 policies | 19 |
| S3 | Bucket terraform state | 1 |

### URL de la API

```
https://aonn2v35n0.execute-api.us-east-2.amazonaws.com/dev
```

### Test end-to-end verificado

```
1. POST /customers       → Cliente creado (Maria González)
2. POST /agents          → Agente creado (Carlos López, ONLINE, skills: billing)
3. POST /tickets         → Ticket creado (OPEN)
4. PUT  /tickets/{id}/assign  → Asignado (ASSIGNED)
5. PUT  /tickets/{id}/start   → En progreso (IN_PROGRESS)
6. PUT  /tickets/{id}/resolve → Resuelto (RESOLVED)
7. GET  /notifications        → 3 notificaciones generadas automáticamente:
                                 - "Tu ticket fue recibido"
                                 - "Tu ticket fue asignado"
                                 - "Tu ticket fue resuelto"
8. GET  /agents               → active_tickets_count = 0 (decrementado tras resolver)
```

### Patrones demostrados en el test

| Paso | Patrón |
|---|---|
| Lambda reutiliza DynamoDB client | **Singleton** |
| Notificación enviada via InternalNotifier | **Factory** |
| Handler tiene logging + error handling + correlation ID | **Decorator** |
| SNS distribuye eventos a 3 SQS queues | **Observer** |
| Agente seleccionado por LeastLoaded | **Strategy** |
| Ticket transiciona OPEN → ASSIGNED → IN_PROGRESS → RESOLVED | **State Machine** |
| customer_name copiado en ticket | **Database per Service + Desnormalización** |
| Correlation ID propagado en headers y eventos | **Tracing Distribuido** |
