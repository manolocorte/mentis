# ===========================================================================
# messaging module — SQS ingest queue + DLQ
# ===========================================================================

locals {
  prefix = "${var.project_name}-${var.environment}"
  # SQS visibility timeout must be >= 6x the consumer Lambda timeout.
  # worker timeout = 120s  =>  6 * 120 = 720s
  visibility_timeout = var.worker_lambda_timeout * 6
}

# ---------------------------------------------------------------------------
# Dead-letter queue
# ---------------------------------------------------------------------------

resource "aws_sqs_queue" "ingest_dlq" {
  name                      = "${local.prefix}-ingest-dlq"
  message_retention_seconds = 1209600 # 14 days
}

# ---------------------------------------------------------------------------
# Ingest queue
# ---------------------------------------------------------------------------

resource "aws_sqs_queue" "ingest" {
  name                       = "${local.prefix}-ingest"
  visibility_timeout_seconds = local.visibility_timeout
  message_retention_seconds  = 86400 # 1 day
  receive_wait_time_seconds  = 10    # long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ingest_dlq.arn
    maxReceiveCount     = 3
  })
}
