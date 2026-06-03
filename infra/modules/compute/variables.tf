variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "lambda_image_uri" {
  type        = string
  description = "ECR image URI shared by all Lambda functions."
}

variable "allowed_origin" {
  type        = string
  default     = "*"
  description = "CORS allow_origins value for the API Gateway HTTP API."
}

variable "harvest_enabled" {
  type        = bool
  default     = false
  description = "Enable/disable the EventBridge Scheduler for the harvester Lambda."
}

variable "cloudfront_url" {
  type        = string
  description = "CloudFront distribution URL (used in Lambda env vars for CORS context)."
}

# ---------------------------------------------------------------------------
# Data module inputs
# ---------------------------------------------------------------------------

variable "table_name" {
  type = string
}

variable "table_arn" {
  type = string
}

variable "documents_bucket_name" {
  type = string
}

variable "documents_bucket_arn" {
  type = string
}

variable "vector_bucket_name" {
  type = string
}

variable "vector_bucket_arn" {
  type = string
}

variable "vector_index_chunks_arn" {
  type = string
}

variable "vector_index_memory_arn" {
  type = string
}

variable "api_key_ssm_arn" {
  type = string
}

variable "unpaywall_email_ssm_arn" {
  type = string
}

variable "university_api_key_ssm_arn" {
  type = string
}

# ---------------------------------------------------------------------------
# Messaging module inputs
# ---------------------------------------------------------------------------

variable "ingest_queue_url" {
  type = string
}

variable "ingest_queue_arn" {
  type = string
}

# ---------------------------------------------------------------------------
# Bedrock model IDs
# ---------------------------------------------------------------------------

variable "bedrock_router_model" {
  type    = string
  default = "anthropic.claude-haiku-4-5-20251001"
}

variable "bedrock_chat_model" {
  type    = string
  default = "anthropic.claude-sonnet-4-6"
}

variable "bedrock_draft_model" {
  type    = string
  default = "anthropic.claude-opus-4-8"
}

variable "bedrock_embed_model" {
  type    = string
  default = "amazon.titan-embed-text-v2:0"
}

variable "embed_dim" {
  type    = number
  default = 1024
}
