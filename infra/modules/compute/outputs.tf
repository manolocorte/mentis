output "api_url" {
  value       = aws_apigatewayv2_stage.default.invoke_url
  description = "HTTP API base URL (e.g. https://<id>.execute-api.<region>.amazonaws.com)."
}

output "api_lambda_arn" {
  value = aws_lambda_function.api.arn
}

output "worker_lambda_arn" {
  value = aws_lambda_function.worker.arn
}

output "harvester_lambda_arn" {
  value = aws_lambda_function.harvester.arn
}
