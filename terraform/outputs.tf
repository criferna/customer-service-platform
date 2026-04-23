# =============================================================================
# Outputs
# =============================================================================

output "api_gateway_url" {
  description = "Base URL of the API Gateway"
  value       = aws_api_gateway_stage.main.invoke_url
}

output "api_gateway_id" {
  description = "API Gateway REST API ID"
  value       = aws_api_gateway_rest_api.main.id
}

output "sns_topic_arn" {
  description = "Domain events SNS topic ARN"
  value       = aws_sns_topic.domain_events.arn
}

output "dynamodb_tables" {
  description = "DynamoDB table names"
  value = {
    customers            = aws_dynamodb_table.customers.name
    tickets              = aws_dynamodb_table.tickets.name
    agents               = aws_dynamodb_table.agents.name
    notifications        = aws_dynamodb_table.notifications.name
    knowledge_categories = aws_dynamodb_table.knowledge_categories.name
    knowledge_articles   = aws_dynamodb_table.knowledge_articles.name
  }
}

output "lambda_functions" {
  description = "Lambda function names"
  value = {
    customers              = aws_lambda_function.customers.function_name
    tickets                = aws_lambda_function.tickets.function_name
    agents                 = aws_lambda_function.agents.function_name
    notifications          = aws_lambda_function.notifications.function_name
    knowledge              = aws_lambda_function.knowledge.function_name
    notifications_consumer = aws_lambda_function.notifications_consumer.function_name
    tickets_consumer       = aws_lambda_function.tickets_consumer.function_name
    agents_consumer        = aws_lambda_function.agents_consumer.function_name
  }
}

output "sqs_queues" {
  description = "SQS queue URLs"
  value = {
    notifications_ticket_events = aws_sqs_queue.notifications_ticket_events.url
    tickets_customer_events     = aws_sqs_queue.tickets_customer_events.url
    agents_ticket_events        = aws_sqs_queue.agents_ticket_events.url
  }
}
