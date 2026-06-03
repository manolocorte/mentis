output "api_url" {
  description = "Invoke URL for the API Gateway HTTP API."
  value       = module.compute.api_url
}

output "cloudfront_url" {
  description = "HTTPS URL of the CloudFront distribution (set this as var.allowed_origin after first deploy)."
  value       = module.frontend.cloudfront_url
}

output "ecr_repository_url" {
  description = "ECR repository URL — push your container image here before deploying Lambdas."
  value       = aws_ecr_repository.app.repository_url
}

output "table_name" {
  description = "DynamoDB single-table name."
  value       = module.data.table_name
}

output "documents_bucket" {
  description = "S3 bucket name for PDF documents."
  value       = module.data.documents_bucket_name
}

output "vector_bucket" {
  description = "S3 Vectors bucket name."
  value       = module.data.vector_bucket_name
}

output "site_bucket" {
  description = "S3 bucket name for the frontend static site (served via CloudFront)."
  value       = module.frontend.site_bucket_name
}

output "ingest_queue_url" {
  description = "SQS ingest queue URL."
  value       = module.messaging.ingest_queue_url
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID — needed for cache invalidation after frontend deploys."
  value       = module.frontend.cloudfront_distribution_id
}
