// =============================================================================
// CAPA DE INFRAESTRUCTURA - Event Publisher (RabbitMQ)
// =============================================================================
// Publica eventos de dominio del Knowledge service al Event Bus.
// =============================================================================

package messaging

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"time"

	amqp "github.com/rabbitmq/amqp091-go"
)

const exchangeName = "domain.events"

// Publisher publica eventos a RabbitMQ.
type Publisher struct {
	conn    *amqp.Connection
	channel *amqp.Channel
}

// DomainEvent estructura estándar de un evento de dominio.
type DomainEvent struct {
	EventID       string      `json:"event_id"`
	EventType     string      `json:"event_type"`
	AggregateType string      `json:"aggregate_type"`
	AggregateID   string      `json:"aggregate_id"`
	OccurredAt    string      `json:"occurred_at"`
	CorrelationID string      `json:"correlation_id,omitempty"`
	Payload       interface{} `json:"payload"`
}

// NewPublisher crea una nueva conexión a RabbitMQ.
func NewPublisher() (*Publisher, error) {
	url := os.Getenv("RABBITMQ_URL")
	if url == "" {
		url = "amqp://guest:guest@localhost:5672/"
	}

	conn, err := amqp.Dial(url)
	if err != nil {
		return nil, err
	}

	ch, err := conn.Channel()
	if err != nil {
		conn.Close()
		return nil, err
	}

	return &Publisher{conn: conn, channel: ch}, nil
}

// Publish publica un evento al exchange domain.events.
func (p *Publisher) Publish(event DomainEvent) error {
	if p == nil || p.channel == nil {
		return nil // Silently skip if not connected (resilience)
	}

	body, err := json.Marshal(event)
	if err != nil {
		return err
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	return p.channel.PublishWithContext(ctx,
		exchangeName,
		event.EventType,
		false,
		false,
		amqp.Publishing{
			ContentType:  "application/json",
			DeliveryMode: amqp.Persistent,
			Body:         body,
			Headers: amqp.Table{
				"event_type":     event.EventType,
				"correlation_id": event.CorrelationID,
				"aggregate_type": event.AggregateType,
			},
		},
	)
}

// Close cierra la conexión a RabbitMQ.
func (p *Publisher) Close() {
	if p.channel != nil {
		p.channel.Close()
	}
	if p.conn != nil {
		p.conn.Close()
	}
	log.Println(`{"level":"INFO","message":"RabbitMQ connection closed"}`)
}
