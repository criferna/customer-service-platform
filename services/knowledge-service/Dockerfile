# =============================================================================
# Dockerfile - Knowledge Service (Go / Gin)
# =============================================================================
# Multi-stage build para Go:
#   Stage 1 (builder): compila el binario estático
#   Stage 2 (runtime): imagen scratch mínima (~15MB total)
#
# Go produce binarios estáticos que no necesitan runtime.
# Esto resulta en la imagen más pequeña de todos los microservicios.
#
# INDEPENDENCIA TECNOLÓGICA (Slide 12):
#   Este servicio usa Go/Gin, demostrando que cada microservicio
#   puede elegir su tecnología. Go es ideal para servicios read-heavy
#   como una base de conocimiento (alto rendimiento, bajo consumo de memoria).
# =============================================================================

# --- Stage 1: Builder ---
FROM golang:1.22-alpine AS builder

WORKDIR /build

# Copiar archivos de módulos primero (cache de dependencias)
COPY go.mod ./
RUN go mod download 2>/dev/null || true

# Copiar código fuente, resolver dependencias y compilar
COPY . .
RUN go mod tidy && CGO_ENABLED=0 GOOS=linux go build -o /knowledge-service ./cmd/main.go

# --- Stage 2: Runtime ---
# Usamos alpine en vez de scratch para tener wget (healthcheck)
FROM alpine:3.19

LABEL service="knowledge-service" \
      team="customer-platform" \
      pattern="microservice"

# Certificados SSL y usuario non-root
RUN apk --no-cache add ca-certificates wget && \
    addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# Copiar solo el binario compilado
COPY --from=builder /knowledge-service .

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=10s \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

CMD ["./knowledge-service"]
