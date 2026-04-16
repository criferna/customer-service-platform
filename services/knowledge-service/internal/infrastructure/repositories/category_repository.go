// =============================================================================
// CAPA DE INFRAESTRUCTURA - Repositorio de Categorías
// =============================================================================

package repositories

import (
	"context"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"

	"knowledge-service/internal/domain/entities"
)

// CategoryRepository maneja la persistencia de categorías.
type CategoryRepository struct {
	db *pgxpool.Pool
}

// NewCategoryRepository crea un nuevo repositorio.
func NewCategoryRepository(db *pgxpool.Pool) *CategoryRepository {
	return &CategoryRepository{db: db}
}

// Create persiste una nueva categoría.
func (r *CategoryRepository) Create(ctx context.Context, cat *entities.Category) (*entities.Category, error) {
	_, err := r.db.Exec(ctx,
		`INSERT INTO categories (id, name, description, created_at, updated_at)
		 VALUES ($1, $2, $3, $4, $5)`,
		cat.ID, cat.Name, cat.Description, cat.CreatedAt, cat.UpdatedAt,
	)
	return cat, err
}

// GetByID obtiene una categoría por ID.
func (r *CategoryRepository) GetByID(ctx context.Context, id uuid.UUID) (*entities.Category, error) {
	cat := &entities.Category{}
	err := r.db.QueryRow(ctx,
		`SELECT id, name, description, created_at, updated_at FROM categories WHERE id = $1`, id,
	).Scan(&cat.ID, &cat.Name, &cat.Description, &cat.CreatedAt, &cat.UpdatedAt)
	if err != nil {
		return nil, err
	}
	return cat, nil
}

// List devuelve todas las categorías.
func (r *CategoryRepository) List(ctx context.Context) ([]*entities.Category, error) {
	rows, err := r.db.Query(ctx,
		`SELECT id, name, description, created_at, updated_at FROM categories ORDER BY name`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var categories []*entities.Category
	for rows.Next() {
		c := &entities.Category{}
		if err := rows.Scan(&c.ID, &c.Name, &c.Description, &c.CreatedAt, &c.UpdatedAt); err != nil {
			return nil, err
		}
		categories = append(categories, c)
	}
	return categories, nil
}
