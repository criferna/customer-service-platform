# =============================================================================
# Dockerfile - Tickets Service (Node.js / Express)
# =============================================================================
# Multi-stage build optimizado para Node.js:
#   Stage 1 (builder): instala dependencias y compila
#   Stage 2 (runtime): solo copia lo necesario para ejecutar
#
# Demuestra independencia tecnológica (Slide 12):
#   Este servicio usa Node.js/Express mientras customers-service usa Python/FastAPI.
#   Ambos se comunican vía API Gateway y Event Bus, sin importar el lenguaje.
# =============================================================================

# --- Stage 1: Builder ---
FROM node:20-alpine AS builder

WORKDIR /build

# Instalar dependencias primero (aprovecha Docker layer cache)
COPY package.json ./
RUN npm install --omit=dev

# --- Stage 2: Runtime ---
FROM node:20-alpine

LABEL service="tickets-service" \
      team="customer-platform" \
      pattern="microservice"

# Crear usuario non-root
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# Copiar dependencias desde builder
COPY --from=builder /build/node_modules ./node_modules

# Copiar código fuente
COPY src/ ./src/
COPY package.json ./

# Cambiar a non-root
USER appuser

EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=20s \
    CMD node -e "fetch('http://localhost:3000/health').then(r=>{if(!r.ok)throw r;process.exit(0)}).catch(()=>process.exit(1))"

CMD ["node", "src/presentation/server.js"]
