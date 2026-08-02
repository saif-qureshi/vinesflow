resource "random_password" "jwt" {
  length  = 64
  special = false
}

# Fernet key for FBR token encryption: URL-safe base64 of exactly 32 random bytes.
resource "random_id" "fbr_key" {
  byte_length = 32
}

locals {
  # b64_std retains the padding Fernet requires; translate only the URL-unsafe characters.
  fbr_encryption_key = replace(replace(random_id.fbr_key.b64_std, "+", "-"), "/", "_")

  backend_env = join("\n", [
    "ENVIRONMENT=production",
    "DATABASE_URL=${local.database_url}",
    "JWT_SECRET=${random_password.jwt.result}",
    "FBR_BASE_URL=${var.fbr_base_url}",
    "FBR_ENCRYPTION_KEY=${local.fbr_encryption_key}",
    "REFRESH_COOKIE_SECURE=true",
    "REFRESH_COOKIE_SAMESITE=lax",
    "BACKEND_CORS_ORIGINS=https://${local.customer_portal_domain},https://${local.admin_portal_domain}",
    "GOTENBERG_URL=http://gotenberg:3000",
    "STORAGE_BACKEND=s3",
    "S3_BUCKET=${aws_s3_bucket.media.bucket}",
    "S3_REGION=${var.region}",
    "S3_PUBLIC_URL=${local.media_url}",
    "MEDIA_KEY_PREFIX=",
    "MAX_UPLOAD_MB=10",
    "CELERY_TASK_ALWAYS_EAGER=false",
    "SQS_QUEUE_NAME=${aws_sqs_queue.jobs.name}",
    "SQS_QUEUE_URL=${aws_sqs_queue.jobs.url}",
    "SQS_REGION=${var.region}",
    "CELERY_VISIBILITY_TIMEOUT=${var.sqs_visibility_timeout}",
  ])
}

# Whole backend .env as one encrypted parameter; the instance fetches it at boot.
resource "aws_ssm_parameter" "backend_env" {
  name  = "/${local.name}/backend_env"
  type  = "SecureString"
  value = local.backend_env
}
