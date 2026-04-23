# =============================================================================
# API Gateway (reemplaza Kong de Docker)
# =============================================================================
# REST API con proxy integration a Lambda.
# Rutas mapean 1:1 con los servicios Docker originales.
#
# Estructura:
#   /api/v1/customers        → customers Lambda
#   /api/v1/customers/{id}   → customers Lambda
#   /api/v1/tickets          → tickets Lambda
#   /api/v1/tickets/{id}     → tickets Lambda
#   /api/v1/tickets/{id}/{action} → tickets Lambda
#   /api/v1/agents           → agents Lambda
#   /api/v1/agents/{id}      → agents Lambda
#   /api/v1/agents/{id}/status → agents Lambda
#   /api/v1/agents/available/next → agents Lambda
#   /api/v1/notifications    → notifications Lambda
#   /api/v1/notifications/{id} → notifications Lambda
#   /api/v1/categories       → knowledge Lambda
#   /api/v1/articles         → knowledge Lambda
#   /api/v1/articles/{id}    → knowledge Lambda
# =============================================================================

resource "aws_api_gateway_rest_api" "main" {
  name        = "${var.prefix}-api"
  description = "Customer Service Platform API (Lab Microservicios)"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# ---------------------------------------------------------------------------
# Base path: /api/v1
# ---------------------------------------------------------------------------
resource "aws_api_gateway_resource" "api" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "api"
}

resource "aws_api_gateway_resource" "v1" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "v1"
}

# ===========================================================================
# CUSTOMERS: /api/v1/customers, /api/v1/customers/{id}
# ===========================================================================
resource "aws_api_gateway_resource" "customers" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "customers"
}

resource "aws_api_gateway_resource" "customers_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.customers.id
  path_part   = "{id}"
}

# Customers collection: GET, POST, OPTIONS
resource "aws_api_gateway_method" "customers_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.customers.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "customers_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.customers.id
  http_method             = aws_api_gateway_method.customers_any.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.customers.invoke_arn
}

# Customers item: GET, PUT, DELETE, OPTIONS
resource "aws_api_gateway_method" "customers_id_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.customers_id.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "customers_id_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.customers_id.id
  http_method             = aws_api_gateway_method.customers_id_any.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.customers.invoke_arn
}

# ===========================================================================
# TICKETS: /api/v1/tickets, /api/v1/tickets/{id}, /api/v1/tickets/{id}/{action}
# ===========================================================================
resource "aws_api_gateway_resource" "tickets" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "tickets"
}

resource "aws_api_gateway_resource" "tickets_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.tickets.id
  path_part   = "{id}"
}

resource "aws_api_gateway_resource" "tickets_id_action" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.tickets_id.id
  path_part   = "{action}"
}

resource "aws_api_gateway_method" "tickets_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.tickets.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "tickets_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.tickets.id
  http_method             = aws_api_gateway_method.tickets_any.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.tickets.invoke_arn
}

resource "aws_api_gateway_method" "tickets_id_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.tickets_id.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "tickets_id_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.tickets_id.id
  http_method             = aws_api_gateway_method.tickets_id_any.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.tickets.invoke_arn
}

resource "aws_api_gateway_method" "tickets_id_action_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.tickets_id_action.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "tickets_id_action_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.tickets_id_action.id
  http_method             = aws_api_gateway_method.tickets_id_action_any.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.tickets.invoke_arn
}

# ===========================================================================
# AGENTS: /api/v1/agents, /api/v1/agents/{id}, /api/v1/agents/{id}/status,
#         /api/v1/agents/available/next
# ===========================================================================
resource "aws_api_gateway_resource" "agents" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "agents"
}

resource "aws_api_gateway_resource" "agents_available" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.agents.id
  path_part   = "available"
}

resource "aws_api_gateway_resource" "agents_available_next" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.agents_available.id
  path_part   = "next"
}

resource "aws_api_gateway_resource" "agents_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.agents.id
  path_part   = "{id}"
}

resource "aws_api_gateway_resource" "agents_id_status" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.agents_id.id
  path_part   = "status"
}

resource "aws_api_gateway_method" "agents_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.agents.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "agents_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.agents.id
  http_method             = aws_api_gateway_method.agents_any.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.agents.invoke_arn
}

resource "aws_api_gateway_method" "agents_id_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.agents_id.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "agents_id_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.agents_id.id
  http_method             = aws_api_gateway_method.agents_id_any.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.agents.invoke_arn
}

resource "aws_api_gateway_method" "agents_id_status_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.agents_id_status.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "agents_id_status_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.agents_id_status.id
  http_method             = aws_api_gateway_method.agents_id_status_any.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.agents.invoke_arn
}

resource "aws_api_gateway_method" "agents_available_next_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.agents_available_next.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "agents_available_next_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.agents_available_next.id
  http_method             = aws_api_gateway_method.agents_available_next_any.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.agents.invoke_arn
}

# ===========================================================================
# NOTIFICATIONS: /api/v1/notifications, /api/v1/notifications/{id}
# ===========================================================================
resource "aws_api_gateway_resource" "notifications" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "notifications"
}

resource "aws_api_gateway_resource" "notifications_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.notifications.id
  path_part   = "{id}"
}

resource "aws_api_gateway_method" "notifications_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.notifications.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "notifications_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.notifications.id
  http_method             = aws_api_gateway_method.notifications_any.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.notifications.invoke_arn
}

resource "aws_api_gateway_method" "notifications_id_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.notifications_id.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "notifications_id_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.notifications_id.id
  http_method             = aws_api_gateway_method.notifications_id_any.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.notifications.invoke_arn
}

# ===========================================================================
# KNOWLEDGE: /api/v1/categories, /api/v1/articles, /api/v1/articles/{id}
# ===========================================================================
resource "aws_api_gateway_resource" "categories" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "categories"
}

resource "aws_api_gateway_resource" "articles" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "articles"
}

resource "aws_api_gateway_resource" "articles_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.articles.id
  path_part   = "{id}"
}

resource "aws_api_gateway_method" "categories_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.categories.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "categories_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.categories.id
  http_method             = aws_api_gateway_method.categories_any.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.knowledge.invoke_arn
}

resource "aws_api_gateway_method" "articles_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.articles.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "articles_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.articles.id
  http_method             = aws_api_gateway_method.articles_any.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.knowledge.invoke_arn
}

resource "aws_api_gateway_method" "articles_id_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.articles_id.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "articles_id_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.articles_id.id
  http_method             = aws_api_gateway_method.articles_id_any.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.knowledge.invoke_arn
}

# ===========================================================================
# Lambda Permissions (permitir que API Gateway invoque cada Lambda)
# ===========================================================================
resource "aws_lambda_permission" "customers_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.customers.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "tickets_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.tickets.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "agents_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.agents.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "notifications_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notifications.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "knowledge_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.knowledge.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# ===========================================================================
# Deployment + Stage
# ===========================================================================
resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode([
      # Redeploy when any method or integration changes
      aws_api_gateway_integration.customers_any.id,
      aws_api_gateway_integration.customers_id_any.id,
      aws_api_gateway_integration.tickets_any.id,
      aws_api_gateway_integration.tickets_id_any.id,
      aws_api_gateway_integration.tickets_id_action_any.id,
      aws_api_gateway_integration.agents_any.id,
      aws_api_gateway_integration.agents_id_any.id,
      aws_api_gateway_integration.agents_id_status_any.id,
      aws_api_gateway_integration.agents_available_next_any.id,
      aws_api_gateway_integration.notifications_any.id,
      aws_api_gateway_integration.notifications_id_any.id,
      aws_api_gateway_integration.categories_any.id,
      aws_api_gateway_integration.articles_any.id,
      aws_api_gateway_integration.articles_id_any.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      caller         = "$context.identity.caller"
      user           = "$context.identity.user"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.prefix}-api"
  retention_in_days = 7
}

# API Gateway account settings for CloudWatch logging
resource "aws_api_gateway_account" "main" {
  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch.arn
}

resource "aws_iam_role" "api_gateway_cloudwatch" {
  name = "${var.prefix}-api-gateway-cloudwatch"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "apigateway.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch" {
  role       = aws_iam_role.api_gateway_cloudwatch.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
  # Nota: AWS resuelve el ARN automáticamente sin account ID para managed policies
}

# ===========================================================================
# CORS: Method Response para OPTIONS (preflight)
# ===========================================================================
# API Gateway con AWS_PROXY delega CORS al Lambda (ya incluido en _response()).
# Para preflight OPTIONS sin Lambda, se necesitaría MOCK integration.
# En este lab, el Lambda handler ya retorna los headers CORS correctos.
}
