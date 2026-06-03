variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "worker_lambda_timeout" {
  type        = number
  default     = 120
  description = "Worker Lambda timeout in seconds. SQS visibility timeout is set to 6x this value."
}
