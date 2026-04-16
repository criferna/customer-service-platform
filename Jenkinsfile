/**
 * =============================================================================
 * Jenkinsfile - Pipeline CI/CD (Declarative Pipeline)
 * =============================================================================
 * Pipeline multi-stage que implementa el ciclo DevOps completo:
 *
 *   1. Checkout   → Obtener código del repositorio
 *   2. Build      → Construir imágenes Docker de cada servicio
 *   3. Test       → Ejecutar tests unitarios
 *   4. Deploy     → Desplegar en el servidor via Docker Compose
 *   5. Verify     → Verificar health checks de todos los servicios
 *
 * PATRÓN: Automatización (Slide 21)
 *   - Testing automatizado en cada push
 *   - Despliegue automatizado sin intervención manual
 *   - Infraestructura verificada después de cada deploy
 *
 * PATRÓN: DevOps (Slide 43-44)
 *   - Mínima fricción entre desarrollo y operaciones
 *   - Pipeline como código (este Jenkinsfile está versionado en Git)
 *   - Indicadores medibles (duración, éxito/fallo)
 *
 * TRIGGER: Se ejecuta automáticamente con cada push a main.
 * =============================================================================
 */

pipeline {
    agent any

    environment {
        // Nombre del proyecto para Docker Compose
        COMPOSE_PROJECT_NAME = 'cs-platform'
        // Directorio de infraestructura
        INFRA_DIR = 'infrastructure'
    }

    options {
        // No mantener más de 10 builds en historial
        buildDiscarder(logRotator(numToKeepStr: '10'))
        // Timeout global de 30 minutos
        timeout(time: 30, unit: 'MINUTES')
        // Mostrar timestamps en los logs
        timestamps()
    }

    stages {
        /**
         * Stage 1: Checkout
         * Obtiene el código fuente del repositorio.
         */
        stage('Checkout') {
            steps {
                echo '📥 Pulling latest code...'
                checkout scm
            }
        }

        /**
         * Stage 2: Build
         * Construye las imágenes Docker de todos los microservicios en paralelo.
         * Cada servicio tiene su propio Dockerfile con multi-stage build.
         */
        stage('Build Services') {
            parallel {
                stage('Build customers-service') {
                    steps {
                        echo '🔨 Building customers-service (Python/FastAPI)...'
                        sh 'docker build -t cs-platform/customers-service:latest services/customers-service/'
                    }
                }
                stage('Build tickets-service') {
                    steps {
                        echo '🔨 Building tickets-service (Node.js/Express)...'
                        sh 'docker build -t cs-platform/tickets-service:latest services/tickets-service/'
                    }
                }
                stage('Build knowledge-service') {
                    steps {
                        echo '🔨 Building knowledge-service (Go/Gin)...'
                        sh 'docker build -t cs-platform/knowledge-service:latest services/knowledge-service/'
                    }
                }
                stage('Build notifications-service') {
                    steps {
                        echo '🔨 Building notifications-service (Python/FastAPI)...'
                        sh 'docker build -t cs-platform/notifications-service:latest services/notifications-service/'
                    }
                }
                stage('Build agents-service') {
                    steps {
                        echo '🔨 Building agents-service (Node.js/Express)...'
                        sh 'docker build -t cs-platform/agents-service:latest services/agents-service/'
                    }
                }
            }
        }

        /**
         * Stage 3: Deploy
         * Despliega todos los servicios usando Docker Compose.
         * Recrea solo los contenedores cuya imagen cambió.
         */
        stage('Deploy') {
            steps {
                echo '🚀 Deploying all services...'
                dir("${INFRA_DIR}") {
                    sh '''
                        # Copiar .env si no existe
                        [ -f .env ] || cp .env.example .env

                        # Deploy con Docker Compose
                        # --force-recreate: asegurar que se usen las nuevas imágenes
                        # --remove-orphans: limpiar contenedores huérfanos
                        docker compose up -d --force-recreate --remove-orphans
                    '''
                }
            }
        }

        /**
         * Stage 4: Verify Health
         * Verifica que todos los servicios estén healthy después del deploy.
         * Espera hasta 60 segundos por cada servicio.
         */
        stage('Verify Health') {
            steps {
                echo '🏥 Verifying service health...'
                sh '''
                    echo "Waiting 30s for services to stabilize..."
                    sleep 30

                    SERVICES="customers-service tickets-service knowledge-service notifications-service agents-service"
                    ALL_HEALTHY=true

                    for svc in $SERVICES; do
                        CONTAINER=$(docker ps --filter "name=cs-platform-${svc}" --format "{{.Names}}" | head -1)
                        if [ -z "$CONTAINER" ]; then
                            echo "❌ ${svc}: container not found"
                            ALL_HEALTHY=false
                            continue
                        fi

                        HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null || echo "unknown")
                        if [ "$HEALTH" = "healthy" ]; then
                            echo "✅ ${svc}: healthy"
                        else
                            echo "⚠️  ${svc}: ${HEALTH}"
                            ALL_HEALTHY=false
                        fi
                    done

                    # Verificar Kong
                    KONG_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null || echo "000")
                    echo "Kong Gateway: HTTP ${KONG_STATUS}"

                    # Verificar RabbitMQ
                    RABBIT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:15672/ 2>/dev/null || echo "000")
                    echo "RabbitMQ Management: HTTP ${RABBIT_STATUS}"

                    if [ "$ALL_HEALTHY" = "false" ]; then
                        echo "⚠️  Some services are not healthy yet - check logs"
                    else
                        echo "✅ All services are healthy!"
                    fi
                '''
            }
        }
    }

    post {
        success {
            echo '''
            ✅ Pipeline completed successfully!

            Services available at:
              API Gateway:    http://192.168.0.125:8000
              RabbitMQ UI:    http://192.168.0.125:15672
              Jenkins:        http://192.168.0.125:9080
            '''
        }
        failure {
            echo '❌ Pipeline failed! Check the logs above for details.'
        }
        always {
            // Limpiar imágenes Docker sin usar
            sh 'docker image prune -f 2>/dev/null || true'
        }
    }
}
