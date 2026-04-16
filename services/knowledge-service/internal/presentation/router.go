// =============================================================================
// CAPA DE PRESENTACIÓN - Router HTTP (Gin)
// =============================================================================
// Configura todas las rutas del servicio de Knowledge Base.
//
// Endpoints:
//   GET    /health                  → Health check
//   GET    /metrics                 → Métricas Prometheus
//   GET    /api/v1/articles         → Listar artículos
//   POST   /api/v1/articles         → Crear artículo
//   GET    /api/v1/articles/:id     → Obtener artículo
//   PUT    /api/v1/articles/:id     → Actualizar artículo
//   DELETE /api/v1/articles/:id     → Eliminar artículo
//   GET    /api/v1/categories       → Listar categorías
//   POST   /api/v1/categories       → Crear categoría
// =============================================================================

package presentation

import (
	"fmt"
	"log"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"knowledge-service/internal/domain/entities"
	"knowledge-service/internal/infrastructure/messaging"
	"knowledge-service/internal/infrastructure/repositories"
)

var (
	httpRequests = prometheus.NewCounterVec(
		prometheus.CounterOpts{Name: "http_requests_total", Help: "Total HTTP requests"},
		[]string{"method", "endpoint", "status"},
	)
	httpDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{Name: "http_request_duration_seconds", Help: "HTTP request latency"},
		[]string{"method", "endpoint"},
	)
)

func init() {
	prometheus.MustRegister(httpRequests, httpDuration)
}

// SetupRouter configura el router Gin con todas las rutas y middleware.
func SetupRouter(db *pgxpool.Pool, publisher *messaging.Publisher, serviceName string) *gin.Engine {
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()

	// Repositorios
	articleRepo := repositories.NewArticleRepository(db)
	categoryRepo := repositories.NewCategoryRepository(db)

	// Middleware de logging y métricas
	r.Use(func(c *gin.Context) {
		start := time.Now()
		c.Next()
		duration := time.Since(start).Seconds()

		if c.Request.URL.Path != "/health" && c.Request.URL.Path != "/metrics" {
			httpRequests.WithLabelValues(c.Request.Method, c.Request.URL.Path, strconv.Itoa(c.Writer.Status())).Inc()
			httpDuration.WithLabelValues(c.Request.Method, c.Request.URL.Path).Observe(duration)

			log.Printf(`{"timestamp":"%s","service":"%s","level":"INFO","message":"%s %s %d %.3fs","correlation_id":"%s"}`,
				time.Now().Format(time.RFC3339), serviceName,
				c.Request.Method, c.Request.URL.Path, c.Writer.Status(), duration,
				c.GetHeader("X-Correlation-ID"))
		}
	})

	// Recovery middleware
	r.Use(gin.Recovery())

	// --- Health check ---
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "healthy", "service": serviceName})
	})

	// --- Métricas Prometheus ---
	r.GET("/metrics", gin.WrapH(promhttp.Handler()))

	// --- API v1: Articles ---
	articles := r.Group("/api/v1/articles")
	{
		// Listar artículos
		articles.GET("", func(c *gin.Context) {
			offset, _ := strconv.Atoi(c.DefaultQuery("skip", "0"))
			limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
			publishedOnly := c.DefaultQuery("published", "false") == "true"

			list, err := articleRepo.List(c.Request.Context(), offset, limit, publishedOnly, nil)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			if list == nil {
				list = []*entities.Article{}
			}
			c.JSON(http.StatusOK, list)
		})

		// Crear artículo
		articles.POST("", func(c *gin.Context) {
			var input struct {
				Title      string    `json:"title" binding:"required"`
				Content    string    `json:"content" binding:"required"`
				CategoryID *uuid.UUID `json:"category_id"`
				Tags       []string  `json:"tags"`
			}
			if err := c.ShouldBindJSON(&input); err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
				return
			}

			article := entities.NewArticle(input.Title, input.Content, input.CategoryID, input.Tags)
			saved, err := articleRepo.Create(c.Request.Context(), article)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}

			// Publicar evento
			if publisher != nil {
				_ = publisher.Publish(messaging.DomainEvent{
					EventID:       uuid.New().String(),
					EventType:     "article.created",
					AggregateType: "Article",
					AggregateID:   saved.ID.String(),
					OccurredAt:    time.Now().Format(time.RFC3339),
					CorrelationID: c.GetHeader("X-Correlation-ID"),
					Payload: map[string]interface{}{
						"id":    saved.ID.String(),
						"title": saved.Title,
					},
				})
			}

			c.JSON(http.StatusCreated, saved)
		})

		// Obtener artículo por ID
		articles.GET("/:id", func(c *gin.Context) {
			id, err := uuid.Parse(c.Param("id"))
			if err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": "invalid UUID"})
				return
			}
			article, err := articleRepo.GetByID(c.Request.Context(), id)
			if err != nil {
				c.JSON(http.StatusNotFound, gin.H{"error": "article not found"})
				return
			}
			c.JSON(http.StatusOK, article)
		})

		// Actualizar artículo
		articles.PUT("/:id", func(c *gin.Context) {
			id, err := uuid.Parse(c.Param("id"))
			if err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": "invalid UUID"})
				return
			}

			article, err := articleRepo.GetByID(c.Request.Context(), id)
			if err != nil {
				c.JSON(http.StatusNotFound, gin.H{"error": "article not found"})
				return
			}

			var input struct {
				Title      string     `json:"title"`
				Content    string     `json:"content"`
				CategoryID *uuid.UUID `json:"category_id"`
				Tags       []string   `json:"tags"`
				Published  *bool      `json:"published"`
			}
			if err := c.ShouldBindJSON(&input); err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
				return
			}

			article.Update(input.Title, input.Content, input.CategoryID, input.Tags)
			if input.Published != nil {
				if *input.Published {
					article.Publish()
				} else {
					article.Unpublish()
				}
			}

			updated, err := articleRepo.Update(c.Request.Context(), article)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, updated)
		})

		// Eliminar artículo
		articles.DELETE("/:id", func(c *gin.Context) {
			id, err := uuid.Parse(c.Param("id"))
			if err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": "invalid UUID"})
				return
			}
			if err := articleRepo.Delete(c.Request.Context(), id); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.Status(http.StatusNoContent)
		})
	}

	// --- API v1: Categories ---
	categories := r.Group("/api/v1/categories")
	{
		categories.GET("", func(c *gin.Context) {
			list, err := categoryRepo.List(c.Request.Context())
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			if list == nil {
				list = []*entities.Category{}
			}
			c.JSON(http.StatusOK, list)
		})

		categories.POST("", func(c *gin.Context) {
			var input struct {
				Name        string `json:"name" binding:"required"`
				Description string `json:"description"`
			}
			if err := c.ShouldBindJSON(&input); err != nil {
				c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
				return
			}

			cat := entities.NewCategory(input.Name, input.Description)
			saved, err := categoryRepo.Create(c.Request.Context(), cat)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to create category: %v", err)})
				return
			}
			c.JSON(http.StatusCreated, saved)
		})
	}

	return r
}
