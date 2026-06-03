output "site_bucket_name" {
  value = aws_s3_bucket.site.id
}

output "site_bucket_arn" {
  value = aws_s3_bucket.site.arn
}

output "cloudfront_domain_name" {
  value = aws_cloudfront_distribution.site.domain_name
}

output "cloudfront_url" {
  value = "https://${aws_cloudfront_distribution.site.domain_name}"
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.site.id
}
