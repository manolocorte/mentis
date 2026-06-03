# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

variable "project_name" {
  type        = string
  default     = "mentis"
  description = "Short project slug used in all resource names."
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Deployment environment (dev | staging | prod)."
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "Primary AWS region."
}

# ---------------------------------------------------------------------------
# Lambda image
# ---------------------------------------------------------------------------

variable "lambda_image_uri" {
  type        = string
  description = "ECR image URI to deploy on all Lambda functions (e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com/mentis-dev:latest)."
}

# ---------------------------------------------------------------------------
# AI / embedding
# ---------------------------------------------------------------------------

variable "embed_dim" {
  type        = number
  default     = 1024
  description = "Embedding vector dimension used for S3 Vectors indexes and passed to Lambda."
}

variable "bedrock_router_model" {
  type        = string
  default     = "anthropic.claude-haiku-4-5-20251001"
  description = "Bedrock model ID used for lightweight routing/classification."
}

variable "bedrock_chat_model" {
  type        = string
  default     = "anthropic.claude-sonnet-4-6"
  description = "Bedrock model ID used for chat/RAG answers."
}

variable "bedrock_draft_model" {
  type        = string
  default     = "anthropic.claude-opus-4-8"
  description = "Bedrock model ID used for long-form draft generation."
}

variable "bedrock_embed_model" {
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
  description = "Bedrock model ID used for text embeddings."
}

# ---------------------------------------------------------------------------
# API / CORS
# ---------------------------------------------------------------------------

variable "allowed_origin" {
  type        = string
  default     = "*"
  description = "CORS allowed origin for the API Gateway HTTP API. Set to the CloudFront URL after first deploy."
}

# ---------------------------------------------------------------------------
# Harvester scheduler
# ---------------------------------------------------------------------------

variable "harvest_enabled" {
  type        = bool
  default     = false
  description = "Whether the nightly EventBridge Scheduler for the harvester is ENABLED."
}
