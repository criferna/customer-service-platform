# =============================================================================
# SNS + SQS (Observer Pattern — reemplaza RabbitMQ de Docker)
# =============================================================================
# Topología:
#   [Lambda] → publish() → [SNS: domain-events]
#                              ├→ [SQS: notifications-ticket-events]  → notifications-consumer
#                              ├→ [SQS: tickets-customer-events]      → tickets-consumer
#                              └→ [SQS: agents-ticket-events]         → agents-consumer
#
# Cada SQS tiene un filter policy para recibir solo los eventos relevantes.
# Dead Letter Queues (DLQ) capturan mensajes que fallan tras N reintentos.
# =============================================================================

# ---------------------------------------------------------------------------
# SNS Topic: Domain Events (el "Subject" del Observer)
# ---------------------------------------------------------------------------
resource "aws_sns_topic" "domain_events" {
  name = "${var.prefix}-domain-events"
  tags = { Purpose = "domain-event-bus" }
}

# ---------------------------------------------------------------------------
# SQS Queues + DLQs
# ---------------------------------------------------------------------------

# --- Notifications: ticket events ---
resource "aws_sqs_queue" "notifications_ticket_events_dlq" {
  name                      = "${var.prefix}-notifications-ticket-events-dlq"
  message_retention_seconds = 1209600 # 14 days
  tags                      = { Service = "notifications", Type = "dlq" }
}

resource "aws_sqs_queue" "notifications_ticket_events" {
  name                       = "${var.prefix}-notifications-ticket-events"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600 # 4 days

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.notifications_ticket_events_dlq.arn
    maxReceiveCount     = 3
  })

  tags = { Service = "notifications" }
}

# --- Tickets: customer events ---
resource "aws_sqs_queue" "tickets_customer_events_dlq" {
  name                      = "${var.prefix}-tickets-customer-events-dlq"
  message_retention_seconds = 1209600
  tags                      = { Service = "tickets", Type = "dlq" }
}

resource "aws_sqs_queue" "tickets_customer_events" {
  name                       = "${var.prefix}-tickets-customer-events"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.tickets_customer_events_dlq.arn
    maxReceiveCount     = 3
  })

  tags = { Service = "tickets" }
}

# --- Agents: ticket events ---
resource "aws_sqs_queue" "agents_ticket_events_dlq" {
  name                      = "${var.prefix}-agents-ticket-events-dlq"
  message_retention_seconds = 1209600
  tags                      = { Service = "agents", Type = "dlq" }
}

resource "aws_sqs_queue" "agents_ticket_events" {
  name                       = "${var.prefix}-agents-ticket-events"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.agents_ticket_events_dlq.arn
    maxReceiveCount     = 3
  })

  tags = { Service = "agents" }
}

# ---------------------------------------------------------------------------
# SQS Queue Policies (permitir que SNS envíe mensajes a las colas)
# ---------------------------------------------------------------------------
resource "aws_sqs_queue_policy" "notifications_ticket_events" {
  queue_url = aws_sqs_queue.notifications_ticket_events.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowSNSPublish"
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.notifications_ticket_events.arn
      Condition = {
        ArnEquals = { "aws:SourceArn" = aws_sns_topic.domain_events.arn }
      }
    }]
  })
}

resource "aws_sqs_queue_policy" "tickets_customer_events" {
  queue_url = aws_sqs_queue.tickets_customer_events.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowSNSPublish"
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.tickets_customer_events.arn
      Condition = {
        ArnEquals = { "aws:SourceArn" = aws_sns_topic.domain_events.arn }
      }
    }]
  })
}

resource "aws_sqs_queue_policy" "agents_ticket_events" {
  queue_url = aws_sqs_queue.agents_ticket_events.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowSNSPublish"
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.agents_ticket_events.arn
      Condition = {
        ArnEquals = { "aws:SourceArn" = aws_sns_topic.domain_events.arn }
      }
    }]
  })
}

# ---------------------------------------------------------------------------
# SNS Subscriptions con Filter Policies
# ---------------------------------------------------------------------------

# Notifications recibe: ticket.created, ticket.assigned, ticket.resolved, ticket.closed
resource "aws_sns_topic_subscription" "notifications_ticket_events" {
  topic_arn = aws_sns_topic.domain_events.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.notifications_ticket_events.arn

  filter_policy = jsonencode({
    event_type = [
      "ticket.created",
      "ticket.assigned",
      "ticket.resolved",
      "ticket.closed"
    ]
  })

  raw_message_delivery = false
}

# Tickets consumer recibe: customer.created, customer.updated, customer.deleted, agent.updated
resource "aws_sns_topic_subscription" "tickets_customer_events" {
  topic_arn = aws_sns_topic.domain_events.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.tickets_customer_events.arn

  filter_policy = jsonencode({
    event_type = [
      "customer.created",
      "customer.updated",
      "customer.deleted",
      "agent.updated"
    ]
  })

  raw_message_delivery = false
}

# Agents consumer recibe: ticket.assigned, ticket.resolved, ticket.closed
resource "aws_sns_topic_subscription" "agents_ticket_events" {
  topic_arn = aws_sns_topic.domain_events.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.agents_ticket_events.arn

  filter_policy = jsonencode({
    event_type = [
      "ticket.assigned",
      "ticket.resolved",
      "ticket.closed"
    ]
  })

  raw_message_delivery = false
}
