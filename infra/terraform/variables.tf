variable "project" {
  type    = string
  default = "vineflow"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "bucket_prefix" {
  description = "Brand prefix used only for globally unique S3 bucket names."
  type        = string
  default     = "vinesflow"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]*[a-z0-9]$", var.bucket_prefix))
    error_message = "bucket_prefix must be a valid lowercase S3 bucket-name prefix."
  }
}

variable "region" {
  description = "AWS region. ap-south-1 (Mumbai) is the cheapest low-latency region for Pakistan."
  type        = string
  default     = "ap-south-1"
}

# ---- DNS / domain -----------------------------------------------------------
variable "domain_name" {
  description = "Apex domain. Vercel serves the customer/admin portals; AWS serves api_subdomain and the assets CDN."
  type        = string
}

variable "api_subdomain" {
  description = "Subdomain for the FastAPI service on AWS (points at the EC2 Elastic IP)."
  type        = string
  default     = "api"
}

variable "customer_portal_subdomain" {
  description = "Vercel-hosted customer portal subdomain included in backend CORS."
  type        = string
  default     = "app"
}

variable "admin_portal_subdomain" {
  description = "Vercel-hosted super-admin portal subdomain included in backend CORS."
  type        = string
  default     = "admin"
}

variable "media_subdomain" {
  description = "Public assets subdomain for media stored behind CloudFront."
  type        = string
  default     = "assets"
}

variable "route53_zone_id" {
  description = "Route53 hosted zone id for domain_name. Leave empty to manage DNS manually (e.g. Cloudflare); records are printed as outputs."
  type        = string
  default     = ""
}

variable "enable_media_domain" {
  description = "Request an ACM certificate for media_subdomain. Route53 activates it automatically; manual DNS requires activate_media_domain after validation."
  type        = bool
  default     = true
}

variable "activate_media_domain" {
  description = "For non-Route53 DNS only: set true after ACM's validation CNAME resolves and the certificate is ISSUED."
  type        = bool
  default     = false
}

# ---- Compute ----------------------------------------------------------------
variable "instance_type" {
  description = "Graviton (ARM) burstable instance. t4g.medium (4GB) is the minimum production tier for the full stack."
  type        = string
  default     = "t4g.medium"
}

variable "ami_id" {
  description = "Pinned Amazon Linux 2023 ARM64 AMI. Leave empty only to resolve the latest AMI dynamically."
  type        = string
  default     = ""
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

  validation {
    condition     = var.ssh_ingress_cidr == "" || can(cidrhost(var.ssh_ingress_cidr, 0))
    error_message = "ssh_ingress_cidr must be empty or a valid CIDR such as 203.0.113.4/32."
  }
}

variable "key_pair_name" {
  description = "Existing EC2 key pair for SSH. Empty = no key (use SSM Session Manager instead)."
  type        = string
  default     = ""
}

variable "ssh_public_key" {
  description = "Optional OpenSSH public key to register as a Terraform-managed EC2 key pair. Mutually exclusive with key_pair_name."
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

variable "log_retention_days" {
  description = "CloudWatch retention for application container logs."
  type        = number
  default     = 30
}

variable "enable_external_health_check" {
  description = "Create a Route53 HTTPS health check and alarm. This works even when authoritative DNS is hosted by Cloudflare."
  type        = bool
  default     = true
}

variable "enable_local_dev_credentials" {
  description = "Create a long-lived IAM access key for local/* media development. Keep disabled unless actively needed."
  type        = bool
  default     = false
}
