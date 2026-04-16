// =============================================================================
// PUNTO DE ENTRADA - Knowledge Service (Go / Gin)
// =============================================================================
// Microservicio de Base de Conocimiento.
// Bounded Context: Artículos de ayuda y categorías para servicio al cliente.
//
// Este servicio demuestra INDEPENDENCIA TECNOLÓGICA (Slide 12):
//   - Escrito en Go mientras otros servicios usan Python y Node.js
//   - Se comunica con el resto vía API Gateway (Kong) y Event Bus (RabbitMQ)
//   - El lenguaje es transparente para los consumidores de la API
//
// Go es ideal para este servicio porque:
//   - La base de conocimiento es read-heavy (muchas lecturas, pocas escrituras)
//   - Go tiene excelente rendimiento con bajo consumo de memoria
//   - El binario compilado resulta en una imagen Docker de ~15MB
// =============================================================================

package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"knowledge-service/internal/infrastructure/database"
	"knowledge-service/internal/infrastructure/messaging"
	"knowledge-service/internal/presentation"
)

func main() {
	serviceName := getEnv("SERVICE_NAME", "knowledge-service")
	port := getEnv("PORT", "8080")

	log.SetFlags(0) // Usamos formato JSON propio
	logInfo(serviceName, "Starting service...")

	// Conectar a PostgreSQL
	db, err := database.Connect()
	if err != nil {
		log.Fatalf(`{"service":"%s","level":"FATAL","message":"Failed to connect to database: %v"}`, serviceName, err)
	}
	defer db.Close()
	logInfo(serviceName, "Connected to database")

	// Conectar al Event Bus (RabbitMQ)
	publisher, err := messaging.NewPublisher()
	if err != nil {
		// No es fatal: el servicio puede funcionar sin RabbitMQ (resiliencia)
		logWarn(serviceName, "Failed to connect to RabbitMQ: "+err.Error())
	} else {
		defer publisher.Close()
		logInfo(serviceName, "Connected to RabbitMQ")
	}

	// Configurar router HTTP (Gin)
	router := presentation.SetupRouter(db, publisher, serviceName)

	// Crear servidor HTTP
	srv := &http.Server{
		Addr:    ":" + port,
		Handler: router,
	}

	// Iniciar servidor en goroutine
	go func() {
		logInfo(serviceName, "Listening on port "+port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf(`{"service":"%s","level":"FATAL","message":"Server failed: %v"}`, serviceName, err)
		}
	}()

	// Graceful Shutdown: esperar señal SIGTERM/SIGINT
	// Docker envía SIGTERM al contenedor antes de matarlo.
	// Esto permite cerrar conexiones limpiamente.
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logInfo(serviceName, "Shutting down gracefully...")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf(`{"service":"%s","level":"FATAL","message":"Server forced to shutdown: %v"}`, serviceName, err)
	}

	logInfo(serviceName, "Server stopped")
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func logInfo(service, msg string) {
	log.Printf(`{"timestamp":"%s","service":"%s","level":"INFO","message":"%s"}`,
		time.Now().Format(time.RFC3339), service, msg)
}

func logWarn(service, msg string) {
	log.Printf(`{"timestamp":"%s","service":"%s","level":"WARN","message":"%s"}`,
		time.Now().Format(time.RFC3339), service, msg)
}
