# =============================================================================
# DynamoDB Tables (reemplaza 5 instancias PostgreSQL de Docker)
# =============================================================================
# Cada Bounded Context tiene su(s) tabla(s) propia(s) — Database per Service.
# Billing mode PAY_PER_REQUEST = Free Tier friendly (sin provisioning).
# =============================================================================

# ---------------------------------------------------------------------------
# Customers Table
# ---------------------------------------------------------------------------
resource "aws_dynamodb_table" "customers" {
  name         = "${var.prefix}-customers"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
  }

  tags = { Service = "customers" }
}

# ---------------------------------------------------------------------------
# Tickets Table
# ---------------------------------------------------------------------------
resource "aws_dynamodb_table" "tickets" {
  name         = "${var.prefix}-tickets"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "customer_id"
    type = "S"
  }

  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "customer-index"
    hash_key        = "customer_id"
    projection_type = "ALL"
  }

  tags = { Service = "tickets" }
}

# ---------------------------------------------------------------------------
# Agents Table
# ---------------------------------------------------------------------------
resource "aws_dynamodb_table" "agents" {
  name         = "${var.prefix}-agents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    projection_type = "ALL"
  }

  tags = { Service = "agents" }
}

# ---------------------------------------------------------------------------
# Notifications Table
# ---------------------------------------------------------------------------
resource "aws_dynamodb_table" "notifications" {
  name         = "${var.prefix}-notifications"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "recipient_id"
    type = "S"
  }

  global_secondary_index {
    name            = "recipient-index"
    hash_key        = "recipient_id"
    projection_type = "ALL"
  }

  tags = { Service = "notifications" }
}

# ---------------------------------------------------------------------------
# Knowledge Categories Table
# ---------------------------------------------------------------------------
resource "aws_dynamodb_table" "knowledge_categories" {
  name         = "${var.prefix}-knowledge-categories"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = { Service = "knowledge" }
}

# ---------------------------------------------------------------------------
# Knowledge Articles Table
# ---------------------------------------------------------------------------
resource "aws_dynamodb_table" "knowledge_articles" {
  name         = "${var.prefix}-knowledge-articles"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "category_id"
    type = "S"
  }

  global_secondary_index {
    name            = "category-index"
    hash_key        = "category_id"
    projection_type = "ALL"
  }

  tags = { Service = "knowledge" }
}
