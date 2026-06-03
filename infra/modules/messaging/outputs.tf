output "ingest_queue_url" {
  value = aws_sqs_queue.ingest.url
}

output "ingest_queue_arn" {
  value = aws_sqs_queue.ingest.arn
}

output "ingest_dlq_arn" {
  value = aws_sqs_queue.ingest_dlq.arn
}
