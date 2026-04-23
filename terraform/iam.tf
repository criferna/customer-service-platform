# =============================================================================
# IAM Roles y Policies para Lambda
# =============================================================================
# Principio de menor privilegio: cada Lambda tiene acceso solo a los
# recursos que necesita.
# =============================================================================

# ---------------------------------------------------------------------------
# Trust policy compartida (Lambda assume role)
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# ---------------------------------------------------------------------------
# Policy base: CloudWatch Logs (todos los Lambdas necesitan esto)
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "lambda_logging" {
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:*:*:*"]
  }
}

resource "aws_iam_policy" "lambda_logging" {
  name   = "${var.prefix}-lambda-logging"
  policy = data.aws_iam_policy_document.lambda_logging.json
}

# ---------------------------------------------------------------------------
# Policy: SNS Publish (para Lambdas que publican eventos)
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "sns_publish" {
  statement {
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.domain_events.arn]
  }
}

resource "aws_iam_policy" "sns_publish" {
  name   = "${var.prefix}-sns-publish"
  policy = data.aws_iam_policy_document.sns_publish.json
}

# ---------------------------------------------------------------------------
# Policy: SQS Consume (para consumers)
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "sqs_consume" {
  statement {
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [
      aws_sqs_queue.notifications_ticket_events.arn,
      aws_sqs_queue.tickets_customer_events.arn,
      aws_sqs_queue.agents_ticket_events.arn,
    ]
  }
}

resource "aws_iam_policy" "sqs_consume" {
  name   = "${var.prefix}-sqs-consume"
  policy = data.aws_iam_policy_document.sqs_consume.json
}

# ===========================================================================
# API Lambda Roles (customers, tickets, agents, notifications, knowledge)
# ===========================================================================

# --- Customers ---
resource "aws_iam_role" "customers_lambda" {
  name               = "${var.prefix}-customers-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "customers_dynamodb" {
  statement {
    actions = [
      "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
      "dynamodb:DeleteItem", "dynamodb:Scan", "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.customers.arn,
      "${aws_dynamodb_table.customers.arn}/index/*",
    ]
  }
}

resource "aws_iam_policy" "customers_dynamodb" {
  name   = "${var.prefix}-customers-dynamodb"
  policy = data.aws_iam_policy_document.customers_dynamodb.json
}

resource "aws_iam_role_policy_attachment" "customers_logging" {
  role       = aws_iam_role.customers_lambda.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

resource "aws_iam_role_policy_attachment" "customers_dynamodb" {
  role       = aws_iam_role.customers_lambda.name
  policy_arn = aws_iam_policy.customers_dynamodb.arn
}

resource "aws_iam_role_policy_attachment" "customers_sns" {
  role       = aws_iam_role.customers_lambda.name
  policy_arn = aws_iam_policy.sns_publish.arn
}

# --- Tickets ---
resource "aws_iam_role" "tickets_lambda" {
  name               = "${var.prefix}-tickets-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "tickets_dynamodb" {
  statement {
    actions = [
      "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
      "dynamodb:DeleteItem", "dynamodb:Scan", "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.tickets.arn,
      "${aws_dynamodb_table.tickets.arn}/index/*",
    ]
  }
}

resource "aws_iam_policy" "tickets_dynamodb" {
  name   = "${var.prefix}-tickets-dynamodb"
  policy = data.aws_iam_policy_document.tickets_dynamodb.json
}

resource "aws_iam_role_policy_attachment" "tickets_logging" {
  role       = aws_iam_role.tickets_lambda.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

resource "aws_iam_role_policy_attachment" "tickets_dynamodb" {
  role       = aws_iam_role.tickets_lambda.name
  policy_arn = aws_iam_policy.tickets_dynamodb.arn
}

resource "aws_iam_role_policy_attachment" "tickets_sns" {
  role       = aws_iam_role.tickets_lambda.name
  policy_arn = aws_iam_policy.sns_publish.arn
}

# --- Agents ---
resource "aws_iam_role" "agents_lambda" {
  name               = "${var.prefix}-agents-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "agents_dynamodb" {
  statement {
    actions = [
      "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
      "dynamodb:DeleteItem", "dynamodb:Scan", "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.agents.arn,
      "${aws_dynamodb_table.agents.arn}/index/*",
    ]
  }
}

resource "aws_iam_policy" "agents_dynamodb" {
  name   = "${var.prefix}-agents-dynamodb"
  policy = data.aws_iam_policy_document.agents_dynamodb.json
}

resource "aws_iam_role_policy_attachment" "agents_logging" {
  role       = aws_iam_role.agents_lambda.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

resource "aws_iam_role_policy_attachment" "agents_dynamodb" {
  role       = aws_iam_role.agents_lambda.name
  policy_arn = aws_iam_policy.agents_dynamodb.arn
}

resource "aws_iam_role_policy_attachment" "agents_sns" {
  role       = aws_iam_role.agents_lambda.name
  policy_arn = aws_iam_policy.sns_publish.arn
}

# --- Notifications (read-only API) ---
resource "aws_iam_role" "notifications_lambda" {
  name               = "${var.prefix}-notifications-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "notifications_dynamodb" {
  statement {
    actions = [
      "dynamodb:GetItem", "dynamodb:Scan", "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.notifications.arn,
      "${aws_dynamodb_table.notifications.arn}/index/*",
    ]
  }
}

resource "aws_iam_policy" "notifications_dynamodb" {
  name   = "${var.prefix}-notifications-dynamodb"
  policy = data.aws_iam_policy_document.notifications_dynamodb.json
}

resource "aws_iam_role_policy_attachment" "notifications_logging" {
  role       = aws_iam_role.notifications_lambda.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

resource "aws_iam_role_policy_attachment" "notifications_dynamodb" {
  role       = aws_iam_role.notifications_lambda.name
  policy_arn = aws_iam_policy.notifications_dynamodb.arn
}

# --- Knowledge ---
resource "aws_iam_role" "knowledge_lambda" {
  name               = "${var.prefix}-knowledge-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "knowledge_dynamodb" {
  statement {
    actions = [
      "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
      "dynamodb:Scan", "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.knowledge_categories.arn,
      aws_dynamodb_table.knowledge_articles.arn,
      "${aws_dynamodb_table.knowledge_articles.arn}/index/*",
    ]
  }
}

resource "aws_iam_policy" "knowledge_dynamodb" {
  name   = "${var.prefix}-knowledge-dynamodb"
  policy = data.aws_iam_policy_document.knowledge_dynamodb.json
}

resource "aws_iam_role_policy_attachment" "knowledge_logging" {
  role       = aws_iam_role.knowledge_lambda.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

resource "aws_iam_role_policy_attachment" "knowledge_dynamodb" {
  role       = aws_iam_role.knowledge_lambda.name
  policy_arn = aws_iam_policy.knowledge_dynamodb.arn
}

resource "aws_iam_role_policy_attachment" "knowledge_sns" {
  role       = aws_iam_role.knowledge_lambda.name
  policy_arn = aws_iam_policy.sns_publish.arn
}

# ===========================================================================
# Consumer Lambda Roles
# ===========================================================================

# --- Notifications Consumer ---
resource "aws_iam_role" "notifications_consumer_lambda" {
  name               = "${var.prefix}-notifications-consumer-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "notifications_consumer_dynamodb" {
  statement {
    actions = [
      "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
      "dynamodb:Scan", "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.notifications.arn,
      "${aws_dynamodb_table.notifications.arn}/index/*",
    ]
  }
}

resource "aws_iam_policy" "notifications_consumer_dynamodb" {
  name   = "${var.prefix}-notifications-consumer-dynamodb"
  policy = data.aws_iam_policy_document.notifications_consumer_dynamodb.json
}

resource "aws_iam_role_policy_attachment" "notifications_consumer_logging" {
  role       = aws_iam_role.notifications_consumer_lambda.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

resource "aws_iam_role_policy_attachment" "notifications_consumer_dynamodb" {
  role       = aws_iam_role.notifications_consumer_lambda.name
  policy_arn = aws_iam_policy.notifications_consumer_dynamodb.arn
}

resource "aws_iam_role_policy_attachment" "notifications_consumer_sqs" {
  role       = aws_iam_role.notifications_consumer_lambda.name
  policy_arn = aws_iam_policy.sqs_consume.arn
}

# --- Tickets Consumer ---
resource "aws_iam_role" "tickets_consumer_lambda" {
  name               = "${var.prefix}-tickets-consumer-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "tickets_consumer_logging" {
  role       = aws_iam_role.tickets_consumer_lambda.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

resource "aws_iam_role_policy_attachment" "tickets_consumer_dynamodb" {
  role       = aws_iam_role.tickets_consumer_lambda.name
  policy_arn = aws_iam_policy.tickets_dynamodb.arn
}

resource "aws_iam_role_policy_attachment" "tickets_consumer_sqs" {
  role       = aws_iam_role.tickets_consumer_lambda.name
  policy_arn = aws_iam_policy.sqs_consume.arn
}

# --- Agents Consumer ---
resource "aws_iam_role" "agents_consumer_lambda" {
  name               = "${var.prefix}-agents-consumer-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "agents_consumer_logging" {
  role       = aws_iam_role.agents_consumer_lambda.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

resource "aws_iam_role_policy_attachment" "agents_consumer_dynamodb" {
  role       = aws_iam_role.agents_consumer_lambda.name
  policy_arn = aws_iam_policy.agents_dynamodb.arn
}

resource "aws_iam_role_policy_attachment" "agents_consumer_sqs" {
  role       = aws_iam_role.agents_consumer_lambda.name
  policy_arn = aws_iam_policy.sqs_consume.arn
}
