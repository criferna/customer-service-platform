// =============================================================================
// CAPA DE DOMINIO - Entidad Category
// =============================================================================
// Categorías para organizar los artículos de la base de conocimiento.
// Ejemplo: "Cuenta", "Facturación", "General".
// =============================================================================

package entities

import (
	"time"

	"github.com/google/uuid"
)

// Category agrupa artículos por tema.
type Category struct {
	ID          uuid.UUID `json:"id"`
	Name        string    `json:"name"`
	Description string    `json:"description,omitempty"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

// NewCategory crea una nueva categoría.
func NewCategory(name, description string) *Category {
	now := time.Now()
	return &Category{
		ID:          uuid.New(),
		Name:        name,
		Description: description,
		CreatedAt:   now,
		UpdatedAt:   now,
	}
}
