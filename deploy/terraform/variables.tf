variable "region" {
  description = "AWS region (must have Bedrock + your model access enabled)."
  type        = string
  default     = "eu-south-2"
}

variable "instance_type" {
  description = "Graviton (arm64) instance type. t4g.small = 2 vCPU / 2 GB (cheapest workable)."
  type        = string
  default     = "t4g.small"
}

variable "volume_size_gb" {
  description = "Root EBS (gp3) size in GB. Holds the OS and app code (rebuilt each boot)."
  type        = number
  default     = 30
}

variable "data_volume_size_gb" {
  description = "Persistent data EBS (gp3) size in GB. Holds the SQLite DB and project file workspaces; SURVIVES instance replacement."
  type        = number
  default     = 10
}

variable "domain" {
  description = "Custom domain to serve on (you point its DNS A record at the Elastic IP). Leave empty to use <eip>.sslip.io, which needs no DNS setup and still gets a real Let's Encrypt cert."
  type        = string
  default     = ""
}

variable "acme_email" {
  description = "Email for Let's Encrypt/ACME registration (optional but recommended)."
  type        = string
  default     = ""
}

variable "git_repo" {
  description = "HTTPS URL of the Mentis repo to deploy."
  type        = string
  default     = "https://github.com/manolocorte/mentis.git"
}

variable "git_ref" {
  description = "Branch or tag to deploy."
  type        = string
  default     = "main"
}

variable "github_token" {
  description = "GitHub PAT with read access, if the repo is private. Leave empty for a public repo. Stored in SSM, not in user-data."
  type        = string
  default     = ""
  sensitive   = true
}

variable "auth_username" {
  description = "Login username for the app."
  type        = string
  default     = "admin"
}

variable "auth_password" {
  description = "Login password — REQUIRED. This is the guard on your Bedrock bill. Use a long random secret."
  type        = string
  sensitive   = true
}

variable "scopus_api_key" {
  description = "Elsevier/Scopus API key (optional)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "scopus_insttoken" {
  description = "Scopus institutional token (optional)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "contact_email" {
  description = "Email for the OpenAlex/Unpaywall polite pool (optional)."
  type        = string
  default     = ""
}

variable "sandbox_memory" {
  description = "Memory cap per sandbox container. Keep below host RAM minus OS/app (e.g. 1g on a 2 GB box)."
  type        = string
  default     = "1g"
}

variable "ssh_ingress_cidr" {
  description = "CIDR allowed to SSH (port 22). Leave empty to disable SSH entirely (use SSM Session Manager instead)."
  type        = string
  default     = ""
}

variable "key_name" {
  description = "Existing EC2 key pair name for SSH. Only needed if ssh_ingress_cidr is set."
  type        = string
  default     = ""
}
