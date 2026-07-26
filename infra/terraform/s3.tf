data "aws_caller_identity" "current" {}

locals {
  media_bucket   = "${local.name}-media-${data.aws_caller_identity.current.account_id}"
  backups_bucket = "${local.name}-backups-${data.aws_caller_identity.current.account_id}"
}

# ---- Media bucket (fully private; read only via CloudFront) ------------------
resource "aws_s3_bucket" "media" {
  bucket = local.media_bucket
  tags   = { Name = local.media_bucket }
}

resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy      = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    id     = "abort-incomplete-mpu"
    status = "Enabled"
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
  # Optional cost saver — untouched media to Infrequent Access after 90 days.
  # rule {
  #   id     = "ia-transition"
  #   status = "Enabled"
  #   transition {
  #     days          = 90
  #     storage_class = "STANDARD_IA"
  #   }
  # }
}

# Read allowed ONLY to the CloudFront distribution (OAC). No public read.
data "aws_iam_policy_document" "media" {
  statement {
    sid       = "AllowCloudFrontRead"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.media.arn}/*"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.media.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "media" {
  bucket = aws_s3_bucket.media.id
  policy = data.aws_iam_policy_document.media.json
}

# ---- Backups bucket (private; nightly pg_dump) ------------------------------
resource "aws_s3_bucket" "backups" {
  bucket = local.backups_bucket
  tags   = { Name = local.backups_bucket }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket                  = aws_s3_bucket.backups.id
  block_public_acls       = true
  block_public_policy      = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    id     = "expire-old-dumps"
    status = "Enabled"
    expiration {
      days = var.backup_retention_days
    }
  }
}
