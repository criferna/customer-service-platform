// =============================================================================
// CAPA DE INFRAESTRUCTURA - Conexión a PostgreSQL
// =============================================================================
// Pool de conexiones a la BD exclusiva de knowledge (cs_knowledge).
//
// PATRÓN: Database per Service
//   Solo se conecta a cs_knowledge. Otros servicios no pueden acceder.
// =============================================================================

package database

import (
	"context"
	"os"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// Connect crea un pool de conexiones a PostgreSQL.
func Connect() (*pgxpool.Pool, error) {
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		dbURL = "postgresql://localhost/cs_knowledge"
	}

	config, err := pgxpool.ParseConfig(dbURL)
	if err != nil {
		return nil, err
	}

	config.MaxConns = 10
	config.MinConns = 2
	config.MaxConnLifetime = 30 * time.Minute

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	pool, err := pgxpool.NewWithConfig(ctx, config)
	if err != nil {
		return nil, err
	}

	// Verificar conexión
	if err := pool.Ping(ctx); err != nil {
		return nil, err
	}

	return pool, nil
}
