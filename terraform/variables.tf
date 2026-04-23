# =============================================================================
# Variables
# =============================================================================

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "prefix" {
  description = "Resource name prefix"
  type        = string
  default     = "lab-ms"
}

variable "lambda_runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.12"
}

variable "lambda_timeout" {
  description = "Default Lambda timeout in seconds"
  type        = number
  default     = 30
}

variable "lambda_memory" {
  description = "Default Lambda memory in MB"
  type        = number
  default     = 128
}

variable "notification_channel" {
  description = "Notification channel: INTERNAL, EMAIL, SNS"
  type        = string
  default     = "INTERNAL"
}

variable "assignment_strategy" {
  description = "Agent assignment strategy: LEAST_LOADED, ROUND_ROBIN, SKILL_BASED"
  type        = string
  default     = "LEAST_LOADED"
}
