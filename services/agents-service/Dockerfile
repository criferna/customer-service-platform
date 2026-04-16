# =============================================================================
# Dockerfile - Agents Service (Node.js / Express)
# =============================================================================
# Gestión de agentes de soporte. Consume eventos de tickets para
# mantener sincronizado el contador de tickets activos (consistencia eventual).
# =============================================================================

FROM node:20-alpine AS builder
WORKDIR /build
COPY package.json package-lock.json* ./
RUN npm ci --only=production

FROM node:20-alpine
LABEL service="agents-service" team="customer-platform" pattern="microservice"
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app
COPY --from=builder /build/node_modules ./node_modules
COPY src/ ./src/
COPY package.json ./
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=20s \
    CMD node -e "fetch('http://localhost:3000/health').then(r=>{if(!r.ok)throw r;process.exit(0)}).catch(()=>process.exit(1))"
CMD ["node", "src/presentation/server.js"]
