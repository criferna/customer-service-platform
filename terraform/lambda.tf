# =============================================================================
# Lambda Functions (reemplaza contenedores Docker)
# =============================================================================
# Cada Lambda incluye el código del handler + shared layer empaquetados.
# El shared layer contiene los 5 patrones de diseño.
# =============================================================================

# ---------------------------------------------------------------------------
# Lambda Layer: shared patterns (Singleton, Factory, Decorator, Observer, Strategy)
# ---------------------------------------------------------------------------
# Lambda layers requieren estructura python/shared/ para ser importables.
# Usamos null_resource para crear la estructura correcta antes de empaquetar.
# ---------------------------------------------------------------------------
resource "null_resource" "build_shared_layer" {
  triggers = {
    # Rebuild cuando cambie cualquier archivo en shared/
    source_hash = sha1(join("", [
      for f in fileset("${path.module}/../aws-lambdas/shared", "*.py") :
      filesha1("${path.module}/../aws-lambdas/shared/${f}")
    ]))
  }

  provisioner "local-exec" {
    command = <<-EOT
      rm -rf ${path.module}/.build/layer
      mkdir -p ${path.module}/.build/layer/python/shared
      cp ${path.module}/../aws-lambdas/shared/*.py ${path.module}/.build/layer/python/shared/
      cd ${path.module}/.build/layer && zip -r ../shared-layer.zip python/
    EOT
  }
}

data "archive_file" "shared_layer" {
  type        = "zip"
  source_dir  = "${path.module}/.build/layer"
  output_path = "${path.module}/.build/shared-layer.zip"
  depends_on  = [null_resource.build_shared_layer]
}

resource "aws_lambda_layer_version" "shared" {
  layer_name          = "${var.prefix}-shared-patterns"
  filename            = data.archive_file.shared_layer.output_path
  source_code_hash    = data.archive_file.shared_layer.output_base64sha256
  compatible_runtimes = [var.lambda_runtime]
  description         = "Shared layer: Singleton, Factory, Decorator, Observer, Strategy patterns"
}

# ---------------------------------------------------------------------------
# Package each Lambda function
# ---------------------------------------------------------------------------
data "archive_file" "customers" {
  type        = "zip"
  source_dir  = "${path.module}/../aws-lambdas/functions/customers"
  output_path = "${path.module}/.build/customers.zip"
}

data "archive_file" "tickets" {
  type        = "zip"
  source_dir  = "${path.module}/../aws-lambdas/functions/tickets"
  output_path = "${path.module}/.build/tickets.zip"
}

data "archive_file" "agents" {
  type        = "zip"
  source_dir  = "${path.module}/../aws-lambdas/functions/agents"
  output_path = "${path.module}/.build/agents.zip"
}

data "archive_file" "notifications" {
  type        = "zip"
  source_dir  = "${path.module}/../aws-lambdas/functions/notifications"
  output_path = "${path.module}/.build/notifications.zip"
}

data "archive_file" "knowledge" {
  type        = "zip"
  source_dir  = "${path.module}/../aws-lambdas/functions/knowledge"
  output_path = "${path.module}/.build/knowledge.zip"
}

data "archive_file" "notifications_consumer" {
  type        = "zip"
  source_dir  = "${path.module}/../aws-lambdas/functions/notifications-consumer"
  output_path = "${path.module}/.build/notifications-consumer.zip"
}

data "archive_file" "tickets_consumer" {
  type        = "zip"
  source_dir  = "${path.module}/../aws-lambdas/functions/tickets-consumer"
  output_path = "${path.module}/.build/tickets-consumer.zip"
}

data "archive_file" "agents_consumer" {
  type        = "zip"
  source_dir  = "${path.module}/../aws-lambdas/functions/agents-consumer"
  output_path = "${path.module}/.build/agents-consumer.zip"
}

# ---------------------------------------------------------------------------
# CloudWatch Log Groups (created before Lambdas to control retention)
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "customers" {
  name              = "/aws/lambda/${var.prefix}-customers"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "tickets" {
  name              = "/aws/lambda/${var.prefix}-tickets"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "agents" {
  name              = "/aws/lambda/${var.prefix}-agents"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "notifications" {
  name              = "/aws/lambda/${var.prefix}-notifications"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "knowledge" {
  name              = "/aws/lambda/${var.prefix}-knowledge"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "notifications_consumer" {
  name              = "/aws/lambda/${var.prefix}-notifications-consumer"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "tickets_consumer" {
  name              = "/aws/lambda/${var.prefix}-tickets-consumer"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "agents_consumer" {
  name              = "/aws/lambda/${var.prefix}-agents-consumer"
  retention_in_days = 7
}

# ---------------------------------------------------------------------------
# Shared environment variables for API Lambdas
# ---------------------------------------------------------------------------
locals {
  common_env = {
    DOMAIN_EVENTS_TOPIC_ARN = aws_sns_topic.domain_events.arn
    NOTIFICATION_CHANNEL    = var.notification_channel
    ASSIGNMENT_STRATEGY     = var.assignment_strategy
  }
}

# ===========================================================================
# API Lambda Functions
# ===========================================================================

resource "aws_lambda_function" "customers" {
  function_name    = "${var.prefix}-customers"
  filename         = data.archive_file.customers.output_path
  source_code_hash = data.archive_file.customers.output_base64sha256
  handler          = "handler.handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  role             = aws_iam_role.customers_lambda.arn
  layers           = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = merge(local.common_env, {
      SERVICE_NAME = "customers-service"
    })
  }

  depends_on = [aws_cloudwatch_log_group.customers]
}

resource "aws_lambda_function" "tickets" {
  function_name    = "${var.prefix}-tickets"
  filename         = data.archive_file.tickets.output_path
  source_code_hash = data.archive_file.tickets.output_base64sha256
  handler          = "handler.handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  role             = aws_iam_role.tickets_lambda.arn
  layers           = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = merge(local.common_env, {
      SERVICE_NAME = "tickets-service"
    })
  }

  depends_on = [aws_cloudwatch_log_group.tickets]
}

resource "aws_lambda_function" "agents" {
  function_name    = "${var.prefix}-agents"
  filename         = data.archive_file.agents.output_path
  source_code_hash = data.archive_file.agents.output_base64sha256
  handler          = "handler.handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  role             = aws_iam_role.agents_lambda.arn
  layers           = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = merge(local.common_env, {
      SERVICE_NAME = "agents-service"
    })
  }

  depends_on = [aws_cloudwatch_log_group.agents]
}

resource "aws_lambda_function" "notifications" {
  function_name    = "${var.prefix}-notifications"
  filename         = data.archive_file.notifications.output_path
  source_code_hash = data.archive_file.notifications.output_base64sha256
  handler          = "handler.handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  role             = aws_iam_role.notifications_lambda.arn
  layers           = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = merge(local.common_env, {
      SERVICE_NAME = "notifications-service"
    })
  }

  depends_on = [aws_cloudwatch_log_group.notifications]
}

resource "aws_lambda_function" "knowledge" {
  function_name    = "${var.prefix}-knowledge"
  filename         = data.archive_file.knowledge.output_path
  source_code_hash = data.archive_file.knowledge.output_base64sha256
  handler          = "handler.handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  role             = aws_iam_role.knowledge_lambda.arn
  layers           = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = merge(local.common_env, {
      SERVICE_NAME = "knowledge-service"
    })
  }

  depends_on = [aws_cloudwatch_log_group.knowledge]
}

# ===========================================================================
# Consumer Lambda Functions (triggered by SQS)
# ===========================================================================

resource "aws_lambda_function" "notifications_consumer" {
  function_name    = "${var.prefix}-notifications-consumer"
  filename         = data.archive_file.notifications_consumer.output_path
  source_code_hash = data.archive_file.notifications_consumer.output_base64sha256
  handler          = "handler.handler"
  runtime          = var.lambda_runtime
  timeout          = 60
  memory_size      = var.lambda_memory
  role             = aws_iam_role.notifications_consumer_lambda.arn
  layers           = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = merge(local.common_env, {
      SERVICE_NAME = "notifications-consumer"
    })
  }

  depends_on = [aws_cloudwatch_log_group.notifications_consumer]
}

resource "aws_lambda_function" "tickets_consumer" {
  function_name    = "${var.prefix}-tickets-consumer"
  filename         = data.archive_file.tickets_consumer.output_path
  source_code_hash = data.archive_file.tickets_consumer.output_base64sha256
  handler          = "handler.handler"
  runtime          = var.lambda_runtime
  timeout          = 60
  memory_size      = var.lambda_memory
  role             = aws_iam_role.tickets_consumer_lambda.arn
  layers           = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = merge(local.common_env, {
      SERVICE_NAME = "tickets-consumer"
    })
  }

  depends_on = [aws_cloudwatch_log_group.tickets_consumer]
}

resource "aws_lambda_function" "agents_consumer" {
  function_name    = "${var.prefix}-agents-consumer"
  filename         = data.archive_file.agents_consumer.output_path
  source_code_hash = data.archive_file.agents_consumer.output_base64sha256
  handler          = "handler.handler"
  runtime          = var.lambda_runtime
  timeout          = 60
  memory_size      = var.lambda_memory
  role             = aws_iam_role.agents_consumer_lambda.arn
  layers           = [aws_lambda_layer_version.shared.arn]

  environment {
    variables = merge(local.common_env, {
      SERVICE_NAME = "agents-consumer"
    })
  }

  depends_on = [aws_cloudwatch_log_group.agents_consumer]
}

# ---------------------------------------------------------------------------
# SQS Event Source Mappings (conecta SQS → Consumer Lambdas)
# ---------------------------------------------------------------------------
resource "aws_lambda_event_source_mapping" "notifications_consumer" {
  event_source_arn                   = aws_sqs_queue.notifications_ticket_events.arn
  function_name                      = aws_lambda_function.notifications_consumer.arn
  batch_size                         = 5
  maximum_batching_window_in_seconds = 10
  function_response_types            = ["ReportBatchItemFailures"]
}

resource "aws_lambda_event_source_mapping" "tickets_consumer" {
  event_source_arn                   = aws_sqs_queue.tickets_customer_events.arn
  function_name                      = aws_lambda_function.tickets_consumer.arn
  batch_size                         = 5
  maximum_batching_window_in_seconds = 10
  function_response_types            = ["ReportBatchItemFailures"]
}

resource "aws_lambda_event_source_mapping" "agents_consumer" {
  event_source_arn                   = aws_sqs_queue.agents_ticket_events.arn
  function_name                      = aws_lambda_function.agents_consumer.arn
  batch_size                         = 5
  maximum_batching_window_in_seconds = 10
  function_response_types            = ["ReportBatchItemFailures"]
}
