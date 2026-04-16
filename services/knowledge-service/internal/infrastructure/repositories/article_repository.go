// =============================================================================
// CAPA DE INFRAESTRUCTURA - Repositorio de Artículos
// =============================================================================
// Abstrae el acceso a datos para la entidad Article.
// PATRÓN: Repository — la capa de Aplicación no sabe de SQL.
// =============================================================================

package repositories

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"

	"knowledge-service/internal/domain/entities"
)

// ArticleRepository maneja la persistencia de artículos.
type ArticleRepository struct {
	db *pgxpool.Pool
}

// NewArticleRepository crea un nuevo repositorio.
func NewArticleRepository(db *pgxpool.Pool) *ArticleRepository {
	return &ArticleRepository{db: db}
}

// Create persiste un nuevo artículo.
func (r *ArticleRepository) Create(ctx context.Context, article *entities.Article) (*entities.Article, error) {
	_, err := r.db.Exec(ctx,
		`INSERT INTO articles (id, title, content, category_id, author_agent_id, author_agent_name, tags, published, created_at, updated_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
		article.ID, article.Title, article.Content, article.CategoryID,
		article.AuthorAgentID, article.AuthorAgentName,
		article.Tags, article.Published, article.CreatedAt, article.UpdatedAt,
	)
	return article, err
}

// GetByID obtiene un artículo por su ID.
func (r *ArticleRepository) GetByID(ctx context.Context, id uuid.UUID) (*entities.Article, error) {
	article := &entities.Article{}
	err := r.db.QueryRow(ctx,
		`SELECT id, title, content, category_id, author_agent_id, author_agent_name, tags, published, created_at, updated_at
		 FROM articles WHERE id = $1`, id,
	).Scan(
		&article.ID, &article.Title, &article.Content, &article.CategoryID,
		&article.AuthorAgentID, &article.AuthorAgentName,
		&article.Tags, &article.Published, &article.CreatedAt, &article.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}
	return article, nil
}

// List devuelve artículos con paginación. Si publishedOnly=true, solo publicados.
func (r *ArticleRepository) List(ctx context.Context, offset, limit int, publishedOnly bool, categoryID *uuid.UUID) ([]*entities.Article, error) {
	query := `SELECT id, title, content, category_id, author_agent_id, author_agent_name, tags, published, created_at, updated_at
			  FROM articles WHERE 1=1`
	args := []interface{}{}
	argIdx := 1

	if publishedOnly {
		query += ` AND published = true`
	}
	if categoryID != nil {
		query += ` AND category_id = $` + string(rune('0'+argIdx))
		args = append(args, *categoryID)
		argIdx++
	}

	query += ` ORDER BY created_at DESC OFFSET $` + itoa(argIdx) + ` LIMIT $` + itoa(argIdx+1)
	args = append(args, offset, limit)

	rows, err := r.db.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var articles []*entities.Article
	for rows.Next() {
		a := &entities.Article{}
		if err := rows.Scan(
			&a.ID, &a.Title, &a.Content, &a.CategoryID,
			&a.AuthorAgentID, &a.AuthorAgentName,
			&a.Tags, &a.Published, &a.CreatedAt, &a.UpdatedAt,
		); err != nil {
			return nil, err
		}
		articles = append(articles, a)
	}
	return articles, nil
}

// Update actualiza un artículo existente.
func (r *ArticleRepository) Update(ctx context.Context, article *entities.Article) (*entities.Article, error) {
	article.UpdatedAt = time.Now()
	_, err := r.db.Exec(ctx,
		`UPDATE articles SET title=$2, content=$3, category_id=$4, tags=$5, published=$6, updated_at=$7
		 WHERE id=$1`,
		article.ID, article.Title, article.Content, article.CategoryID,
		article.Tags, article.Published, article.UpdatedAt,
	)
	return article, err
}

// Delete elimina un artículo.
func (r *ArticleRepository) Delete(ctx context.Context, id uuid.UUID) error {
	_, err := r.db.Exec(ctx, `DELETE FROM articles WHERE id = $1`, id)
	return err
}

func itoa(i int) string {
	return string(rune('0' + i))
}
