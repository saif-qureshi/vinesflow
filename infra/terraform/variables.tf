variable "project" {
  type    = string
  default = "vineflow"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "region" {
  description = "AWS region. ap-south-1 (Mumbai) is the cheapest low-latency region for Pakistan."
  type        = string
  default     = "ap-south-1"
}

# ---- DNS / domain -----------------------------------------------------------
variable "domain_name" {
  description = "Apex domain, e.g. vineflow.app. The app is served at app_subdomain, media at media_subdomain."
  type        = string
}

variable "app_subdomain" {
  description = "Subdomain the application is served on (points at the EC2 Elastic IP)."
  type        = string
  default     = "app"
}

variable "media_subdomain" {
  description = "Subdomain for media (points at CloudFront)."
  type        = string
  default     = "media"
}

variable "route53_zone_id" {
  description = "Route53 hosted zone id for domain_name. Leave empty to manage DNS manually (e.g. Cloudflare); records are printed as outputs."
  type        = string
  default     = ""
}

variable "enable_media_domain" {
  description = "Serve media at media_subdomain via CloudFront + ACM. If false, media uses the default *.cloudfront.net domain (no DNS/cert work)."
  type        = bool
  default     = true
}

# ---- Compute ----------------------------------------------------------------
variable "instance_type" {
  description = "Graviton (ARM) burstable. t4g.small (2GB) fits the stack with the standalone frontend; t4g.medium (4GB) is the comfortable tier."
  type        = string
  default     = "t4g.small"
}

variable "root_volume_gb" {
  type    = number
  default = 30
}

variable "swap_gb" {
  description = "Swap file size (safety net for Gotenberg/Chromium memory spikes). 0 to disable."
  type        = number
  default     = 3
}

variable "docker_compose_version" {
  description = "Pinned Docker Compose release installed by cloud-init."
  type        = string
  default     = "v2.39.1"
}

variable "ssh_ingress_cidr" {
  description = "CIDR allowed to SSH (port 22). Set to your IP/32. Empty disables SSH ingress (use SSM Session Manager)."
  type        = string
  default     = ""
}

variable "key_pair_name" {
  description = "Existing EC2 key pair for SSH. Empty = no key (use SSM Session Manager instead)."
  type        = string
  default     = ""
}

# ---- Database ---------------------------------------------------------------
variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_allocated_gb" {
  type    = number
  default = 20
}

variable "db_multi_az" {
  description = "Multi-AZ failover (roughly doubles RDS cost). Off for the Comfortable tier."
  type        = bool
  default     = false
}

variable "db_backup_retention_days" {
  type    = number
  default = 14
}

variable "sqs_visibility_timeout" {
  description = "SQS visibility timeout (s). Must exceed the longest Celery task; matches CELERY_VISIBILITY_TIMEOUT."
  type        = number
  default     = 3600
}

variable "db_name" {
  type    = string
  default = "vineflow"
}

variable "db_username" {
  type    = string
  default = "vineflow"
}

# ---- App config (non-secret) ------------------------------------------------
variable "fbr_base_url" {
  type    = string
  default = "https://gw.fbr.gov.pk"
}

variable "alarm_email" {
  description = "Email subscribed to CloudWatch alarms (SNS) and budget alerts. Empty disables notifications."
  type        = string
  default     = ""
}

variable "monthly_budget_usd" {
  description = "Monthly cost budget; emails alarm_email at 80% actual and 100% forecasted spend."
  type        = number
  default     = 50
}

variable "backup_retention_days" {
  description = "How long nightly DB dumps live in the backups bucket."
  type        = number
  default     = 14
}

variable "enable_local_dev_credentials" {
  description = "Create a long-lived IAM access key for local/* media development. Keep disabled unless actively needed."
  type        = bool
  default     = false
}
