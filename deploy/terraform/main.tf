terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

# Latest Amazon Linux 2023 arm64 AMI (via DescribeImages).
data "aws_ami" "al2023_arm64" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-arm64"]
  }
  filter {
    name   = "architecture"
    values = ["arm64"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Default VPC + a subnet (default-VPC subnets are public).
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Default KMS key used by SSM SecureString (needed for the instance to decrypt secrets).
data "aws_kms_alias" "ssm" {
  name = "alias/aws/ssm"
}

locals {
  name = "mentis"
  # Hostname Caddy serves on: custom domain if given, else <eip>.sslip.io (resolved at boot).
}

# --- Networking ------------------------------------------------------------
resource "aws_security_group" "mentis" {
  name        = "${local.name}-sg"
  description = "Mentis app: HTTP/HTTPS in, optional SSH"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP (Caddy ACME + redirect)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  dynamic "ingress" {
    for_each = var.ssh_ingress_cidr == "" ? [] : [var.ssh_ingress_cidr]
    content {
      description = "SSH"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-sg" }
}

# --- IAM: instance role (Bedrock + SSM read + Session Manager) -------------
resource "aws_iam_role" "mentis" {
  name = "${local.name}-ec2-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Session Manager (shell without an open SSH port).
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.mentis.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "mentis" {
  name = "${local.name}-policy"
  role = aws_iam_role.mentis.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "Bedrock"
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
        Resource = "*"
      },
      {
        Sid      = "ReadSecrets"
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"]
        Resource = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/mentis/*"
      },
      {
        Sid      = "DecryptSecrets"
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = data.aws_kms_alias.ssm.target_key_arn
      }
    ]
  })
}

resource "aws_iam_instance_profile" "mentis" {
  name = "${local.name}-profile"
  role = aws_iam_role.mentis.name
}

# --- Secrets in SSM (SecureString; pulled into the box's .env at boot) ------
resource "aws_ssm_parameter" "auth_password" {
  name  = "/mentis/auth_password"
  type  = "SecureString"
  value = var.auth_password
}

resource "aws_ssm_parameter" "scopus_api_key" {
  count = var.scopus_api_key == "" ? 0 : 1
  name  = "/mentis/scopus_api_key"
  type  = "SecureString"
  value = var.scopus_api_key
}

resource "aws_ssm_parameter" "scopus_insttoken" {
  count = var.scopus_insttoken == "" ? 0 : 1
  name  = "/mentis/scopus_insttoken"
  type  = "SecureString"
  value = var.scopus_insttoken
}

resource "aws_ssm_parameter" "github_token" {
  count = var.github_token == "" ? 0 : 1
  name  = "/mentis/github_token"
  type  = "SecureString"
  value = var.github_token
}

# --- Elastic IP (stable address; also feeds the sslip.io hostname) ----------
resource "aws_eip" "mentis" {
  domain = "vpc"
  tags   = { Name = "${local.name}-eip" }
}

# --- The instance ----------------------------------------------------------
resource "aws_instance" "mentis" {
  ami                         = data.aws_ami.al2023_arm64.id
  instance_type               = var.instance_type
  subnet_id                   = data.aws_subnets.default.ids[0]
  vpc_security_group_ids      = [aws_security_group.mentis.id]
  iam_instance_profile        = aws_iam_instance_profile.mentis.name
  associate_public_ip_address = true
  key_name                    = var.key_name == "" ? null : var.key_name

  metadata_options {
    http_tokens   = "required" # IMDSv2 only
    http_endpoint = "enabled"
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = var.volume_size_gb
    encrypted   = true
  }

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    region         = var.region
    eip            = aws_eip.mentis.public_ip
    domain         = var.domain
    acme_email     = var.acme_email
    git_repo       = var.git_repo
    git_ref        = var.git_ref
    auth_username  = var.auth_username
    contact_email  = var.contact_email
    sandbox_memory = var.sandbox_memory
    has_scopus_key = var.scopus_api_key == "" ? "0" : "1"
    has_scopus_tok = var.scopus_insttoken == "" ? "0" : "1"
    has_gh_token   = var.github_token == "" ? "0" : "1"
  })

  user_data_replace_on_change = true

  tags = { Name = local.name }
}

resource "aws_eip_association" "mentis" {
  instance_id   = aws_instance.mentis.id
  allocation_id = aws_eip.mentis.id
}
