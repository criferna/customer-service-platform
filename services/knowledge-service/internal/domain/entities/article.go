// =============================================================================
// CAPA DE DOMINIO - Entidad Article
// =============================================================================
// Representa un artículo de la base de conocimiento.
// En DDD, las entidades tienen identidad propia y ciclo de vida.
//
// Los artículos son el recurso principal de este Bounded Context.
// Son creados por agentes y consultados por clientes y agentes.
//
// PRINCIPIO: Alta Cohesión (Slide 16)
//   Este servicio SOLO se encarga de artículos y categorías.
//   No gestiona tickets, clientes ni agentes.
// =============================================================================

package entities

import (
	"time"

	"github.com/google/uuid"
)

// Article representa un artículo de la base de conocimiento.
type Article struct {
	ID              uuid.UUID `json:"id"`
	Title           string    `json:"title"`
	Content         string    `json:"content"`
	CategoryID      *uuid.UUID `json:"category_id,omitempty"`
	AuthorAgentID   *uuid.UUID `json:"author_agent_id,omitempty"`
	AuthorAgentName *string   `json:"author_agent_name,omitempty"`
	Tags            []string  `json:"tags"`
	Published       bool      `json:"published"`
	CreatedAt       time.Time `json:"created_at"`
	UpdatedAt       time.Time `json:"updated_at"`
}

// NewArticle crea un nuevo artículo con valores por defecto.
func NewArticle(title, content string, categoryID *uuid.UUID, tags []string) *Article {
	now := time.Now()
	return &Article{
		ID:         uuid.New(),
		Title:      title,
		Content:    content,
		CategoryID: categoryID,
		Tags:       tags,
		Published:  false,
		CreatedAt:  now,
		UpdatedAt:  now,
	}
}

// Publish marca el artículo como publicado (visible para clientes).
func (a *Article) Publish() {
	a.Published = true
	a.UpdatedAt = time.Now()
}

// Unpublish oculta el artículo (solo visible para agentes).
func (a *Article) Unpublish() {
	a.Published = false
	a.UpdatedAt = time.Now()
}

// Update actualiza los campos del artículo.
func (a *Article) Update(title, content string, categoryID *uuid.UUID, tags []string) {
	if title != "" {
		a.Title = title
	}
	if content != "" {
		a.Content = content
	}
	if categoryID != nil {
		a.CategoryID = categoryID
	}
	if tags != nil {
		a.Tags = tags
	}
	a.UpdatedAt = time.Now()
}
