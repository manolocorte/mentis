# ---------------------------------------------------------------------------
# Mentis — serverless research assistant
# Single-root composition, all modules wired here.
# ---------------------------------------------------------------------------

locals {
  prefix = "${var.project_name}-${var.environment}"
}

# ---------------------------------------------------------------------------
# ECR repository (shared by all Lambda functions)
# ---------------------------------------------------------------------------

resource "aws_ecr_repository" "app" {
  name                 = local.prefix
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 5 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = { type = "expire" }
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------

module "data" {
  source = "./modules/data"

  project_name = var.project_name
  environment  = var.environment
  embed_dim    = var.embed_dim
}

module "messaging" {
  source = "./modules/messaging"

  project_name         = var.project_name
  environment          = var.environment
  worker_lambda_timeout = 120 # must match compute module worker timeout
}

module "frontend" {
  source = "./modules/frontend"

  project_name = var.project_name
  environment  = var.environment
}

module "compute" {
  source = "./modules/compute"

  project_name   = var.project_name
  environment    = var.environment
  aws_region     = var.aws_region
  allowed_origin = var.allowed_origin
  harvest_enabled = var.harvest_enabled

  lambda_image_uri = var.lambda_image_uri

  # Data module outputs
  table_name             = module.data.table_name
  table_arn              = module.data.table_arn
  documents_bucket_name  = module.data.documents_bucket_name
  documents_bucket_arn   = module.data.documents_bucket_arn
  vector_bucket_name     = module.data.vector_bucket_name
  vector_bucket_arn      = module.data.vector_bucket_arn
  vector_index_chunks_arn = module.data.vector_index_chunks_arn
  vector_index_memory_arn = module.data.vector_index_memory_arn
  api_key_ssm_arn        = module.data.api_key_ssm_arn
  unpaywall_email_ssm_arn = module.data.unpaywall_email_ssm_arn
  university_api_key_ssm_arn = module.data.university_api_key_ssm_arn

  # Messaging module outputs
  ingest_queue_url = module.messaging.ingest_queue_url
  ingest_queue_arn = module.messaging.ingest_queue_arn

  # CloudFront URL for CORS
  cloudfront_url = module.frontend.cloudfront_url

  # Bedrock model IDs
  bedrock_router_model = var.bedrock_router_model
  bedrock_chat_model   = var.bedrock_chat_model
  bedrock_draft_model  = var.bedrock_draft_model
  bedrock_embed_model  = var.bedrock_embed_model
  embed_dim            = var.embed_dim
}
