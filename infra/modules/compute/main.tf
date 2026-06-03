# ===========================================================================
# compute module — IAM roles, Lambda functions, API Gateway v2, EventBridge
# ===========================================================================

locals {
  prefix = "${var.project_name}-${var.environment}"

  # Shared environment variables injected into every Lambda
  common_env = {
    APP_ENV              = var.environment
    AWS_REGION_NAME      = var.aws_region
    TABLE_NAME           = var.table_name
    DOCUMENTS_BUCKET     = var.documents_bucket_name
    VECTOR_BUCKET        = var.vector_bucket_name
    VECTOR_INDEX_CHUNKS  = "chunks"
    VECTOR_INDEX_MEMORY  = "memory"
    BEDROCK_REGION       = var.aws_region
    BEDROCK_ROUTER_MODEL = var.bedrock_router_model
    BEDROCK_CHAT_MODEL   = var.bedrock_chat_model
    BEDROCK_DRAFT_MODEL  = var.bedrock_draft_model
    BEDROCK_EMBED_MODEL  = var.bedrock_embed_model
    BEDROCK_EMBED_DIM    = tostring(var.embed_dim)
    API_KEY_SSM          = "/mentis/${var.environment}/api_key"
    UNPAYWALL_EMAIL_SSM  = "/mentis/${var.environment}/unpaywall_email"
  }
}

data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------
# IAM — shared assume-role policy document
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# ---------------------------------------------------------------------------
# IAM — reusable inline policy documents
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "logs" {
  statement {
    sid     = "CloudWatchLogs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:*:*:*"]
  }
}

data "aws_iam_policy_document" "dynamo" {
  statement {
    sid = "DynamoCRUD"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem",
      "dynamodb:TransactWriteItems",
      "dynamodb:TransactGetItems",
    ]
    resources = [
      var.table_arn,
      "${var.table_arn}/index/GSI1",
    ]
  }
}

data "aws_iam_policy_document" "s3_documents" {
  statement {
    sid = "S3DocumentsReadWrite"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${var.documents_bucket_arn}/*"]
  }

  statement {
    sid     = "S3DocumentsList"
    actions = ["s3:ListBucket"]
    resources = [var.documents_bucket_arn]
  }
}

data "aws_iam_policy_document" "s3_vectors" {
  statement {
    sid = "S3VectorsBucketReadWrite"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = ["${var.vector_bucket_arn}/*"]
  }

  statement {
    sid = "S3VectorsIndexOperations"
    actions = [
      "s3vectors:PutVectors",
      "s3vectors:GetVectors",
      "s3vectors:QueryVectors",
      "s3vectors:ListVectors",
    ]
    resources = [
      var.vector_index_chunks_arn,
      var.vector_index_memory_arn,
    ]
  }
}

data "aws_iam_policy_document" "bedrock" {
  statement {
    sid = "BedrockInvoke"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:Converse",
      "bedrock:ConverseStream",
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "ssm_params" {
  statement {
    sid = "SSMGetParams"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
    ]
    resources = [
      var.api_key_ssm_arn,
      var.unpaywall_email_ssm_arn,
      var.university_api_key_ssm_arn,
    ]
  }
}

data "aws_iam_policy_document" "sqs_producer" {
  statement {
    sid     = "SQSProducer"
    actions = ["sqs:SendMessage"]
    resources = [var.ingest_queue_arn]
  }
}

data "aws_iam_policy_document" "sqs_consumer" {
  statement {
    sid = "SQSConsumer"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:SendMessage", # needed for report_batch_item_failures DLQ
    ]
    resources = [var.ingest_queue_arn]
  }
}

# ===========================================================================
# API Lambda
# ===========================================================================

# IAM
resource "aws_iam_role" "api" {
  name               = "${local.prefix}-api-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "api_combined" {
  source_policy_documents = [
    data.aws_iam_policy_document.logs.json,
    data.aws_iam_policy_document.dynamo.json,
    data.aws_iam_policy_document.s3_documents.json,
    data.aws_iam_policy_document.s3_vectors.json,
    data.aws_iam_policy_document.bedrock.json,
    data.aws_iam_policy_document.ssm_params.json,
    data.aws_iam_policy_document.sqs_producer.json, # api sends ingest jobs
  ]
}

resource "aws_iam_role_policy" "api" {
  name   = "${local.prefix}-api-policy"
  role   = aws_iam_role.api.id
  policy = data.aws_iam_policy_document.api_combined.json
}

# Lambda function
resource "aws_lambda_function" "api" {
  function_name = "${local.prefix}-api"
  role          = aws_iam_role.api.arn
  package_type  = "Image"
  image_uri     = var.lambda_image_uri
  architectures = ["arm64"]
  memory_size   = 1024
  timeout       = 30

  image_config {
    command = ["mentis.adapters.inbound.api.handler"]
  }

  environment {
    variables = merge(local.common_env, {
      INGEST_QUEUE_URL = var.ingest_queue_url
    })
  }
}

resource "aws_cloudwatch_log_group" "api_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = 14
}

# ===========================================================================
# API Gateway v2 HTTP API
# ===========================================================================

resource "aws_apigatewayv2_api" "api" {
  name          = "${local.prefix}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = [var.allowed_origin]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization", "X-Api-Key", "x-api-key"]
    max_age       = 3600
  }
}

resource "aws_cloudwatch_log_group" "api_gw" {
  name              = "/aws/apigateway/${local.prefix}"
  retention_in_days = 14
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn
    format = jsonencode({
      requestId        = "$context.requestId"
      ip               = "$context.identity.sourceIp"
      requestTime      = "$context.requestTime"
      httpMethod       = "$context.httpMethod"
      routeKey         = "$context.routeKey"
      status           = "$context.status"
      protocol         = "$context.protocol"
      responseLength   = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
    })
  }
}

resource "aws_apigatewayv2_integration" "api_lambda" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "catch_all" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.api_lambda.id}"
}

resource "aws_lambda_permission" "api_gw_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

# ===========================================================================
# Worker Lambda (SQS consumer)
# ===========================================================================

# IAM
resource "aws_iam_role" "worker" {
  name               = "${local.prefix}-worker-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "worker_combined" {
  source_policy_documents = [
    data.aws_iam_policy_document.logs.json,
    data.aws_iam_policy_document.dynamo.json,
    data.aws_iam_policy_document.s3_documents.json,
    data.aws_iam_policy_document.s3_vectors.json,
    data.aws_iam_policy_document.bedrock.json,
    data.aws_iam_policy_document.ssm_params.json,
    data.aws_iam_policy_document.sqs_consumer.json,
  ]
}

resource "aws_iam_role_policy" "worker" {
  name   = "${local.prefix}-worker-policy"
  role   = aws_iam_role.worker.id
  policy = data.aws_iam_policy_document.worker_combined.json
}

# Lambda function
resource "aws_lambda_function" "worker" {
  function_name = "${local.prefix}-worker"
  role          = aws_iam_role.worker.arn
  package_type  = "Image"
  image_uri     = var.lambda_image_uri
  architectures = ["arm64"]
  memory_size   = 1024
  timeout       = 120

  image_config {
    command = ["mentis.adapters.inbound.worker.handler"]
  }

  environment {
    variables = local.common_env
  }
}

resource "aws_cloudwatch_log_group" "worker_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.worker.function_name}"
  retention_in_days = 14
}

# SQS event source mapping
resource "aws_lambda_event_source_mapping" "worker_sqs" {
  event_source_arn                   = var.ingest_queue_arn
  function_name                      = aws_lambda_function.worker.arn
  batch_size                         = 5
  maximum_batching_window_in_seconds = 10
  enabled                            = true

  function_response_types = ["ReportBatchItemFailures"]
}

# ===========================================================================
# Harvester Lambda (EventBridge Scheduler nightly trigger)
# ===========================================================================

# IAM
resource "aws_iam_role" "harvester" {
  name               = "${local.prefix}-harvester-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "harvester_combined" {
  source_policy_documents = [
    data.aws_iam_policy_document.logs.json,
    data.aws_iam_policy_document.dynamo.json,
    data.aws_iam_policy_document.ssm_params.json,
    data.aws_iam_policy_document.sqs_producer.json, # publishes to ingest queue
  ]
}

resource "aws_iam_role_policy" "harvester" {
  name   = "${local.prefix}-harvester-policy"
  role   = aws_iam_role.harvester.id
  policy = data.aws_iam_policy_document.harvester_combined.json
}

# Lambda function
resource "aws_lambda_function" "harvester" {
  function_name = "${local.prefix}-harvester"
  role          = aws_iam_role.harvester.arn
  package_type  = "Image"
  image_uri     = var.lambda_image_uri
  architectures = ["arm64"]
  memory_size   = 512
  timeout       = 120

  image_config {
    command = ["mentis.adapters.inbound.harvester.handler"]
  }

  environment {
    variables = merge(local.common_env, {
      INGEST_QUEUE_URL = var.ingest_queue_url
    })
  }
}

resource "aws_cloudwatch_log_group" "harvester_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.harvester.function_name}"
  retention_in_days = 14
}

# ---------------------------------------------------------------------------
# EventBridge Scheduler — IAM role for invoking the harvester Lambda
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${local.prefix}-scheduler-exec"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

resource "aws_iam_role_policy" "scheduler_invoke" {
  name = "${local.prefix}-scheduler-invoke"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "InvokeHarvester"
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.harvester.arn
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# EventBridge Scheduler — nightly 03:00 UTC
# ---------------------------------------------------------------------------

resource "aws_scheduler_schedule" "harvester_nightly" {
  name       = "${local.prefix}-harvester-nightly"
  group_name = "default"

  # Toggle via var.harvest_enabled so dev stays off by default
  state = var.harvest_enabled ? "ENABLED" : "DISABLED"

  schedule_expression          = "cron(0 3 * * ? *)"
  schedule_expression_timezone = "UTC"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.harvester.arn
    role_arn = aws_iam_role.scheduler.arn

    retry_policy {
      maximum_retry_attempts       = 2
      maximum_event_age_in_seconds = 3600
    }
  }
}
