locals {
  media_domain              = "${var.media_subdomain}.${var.domain_name}"
  api_domain                = "${var.api_subdomain}.${var.domain_name}"
  customer_portal_domain    = "${var.customer_portal_subdomain}.${var.domain_name}"
  admin_portal_domain       = "${var.admin_portal_subdomain}.${var.domain_name}"
  use_route53               = var.route53_zone_id != ""
  request_media_certificate = var.enable_media_domain
  use_manual_media_domain   = var.enable_media_domain && !local.use_route53 && var.activate_media_domain
  use_custom_domain         = var.enable_media_domain && (local.use_route53 || var.activate_media_domain)
  media_url                 = local.use_custom_domain ? "https://${local.media_domain}" : "https://${aws_cloudfront_distribution.media.domain_name}"
}

# ACM cert for the media domain (CloudFront requires us-east-1). Route53-validated.
resource "aws_acm_certificate" "media" {
  count             = local.request_media_certificate ? 1 : 0
  provider          = aws.us_east_1
  domain_name       = local.media_domain
  validation_method = "DNS"
  lifecycle { create_before_destroy = true }
}

# Auto-created only when using Route53. On Cloudflare you add the CNAME yourself (see acm_validation_record output).
resource "aws_route53_record" "media_cert_validation" {
  for_each = local.request_media_certificate && local.use_route53 ? {
    for dvo in aws_acm_certificate.media[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  } : {}

  zone_id         = var.route53_zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 300
  allow_overwrite = true
}

# Route53 can complete validation within one apply. Manual DNS intentionally skips
# this waiter so the first apply can return the CNAME instead of blocking for an hour.
resource "aws_acm_certificate_validation" "media" {
  count                   = local.request_media_certificate && local.use_route53 ? 1 : 0
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.media[0].arn
  validation_record_fqdns = [for r in aws_route53_record.media_cert_validation : r.fqdn]
  timeouts {
    create = "60m"
  }
}

# On Cloudflare, the operator adds ACM's CNAME after the first apply and flips
# activate_media_domain only after ACM reports ISSUED. This lookup enforces that state.
data "aws_acm_certificate" "media_issued" {
  count       = local.use_manual_media_domain ? 1 : 0
  provider    = aws.us_east_1
  domain      = local.media_domain
  statuses    = ["ISSUED"]
  types       = ["AMAZON_ISSUED"]
  most_recent = true

  depends_on = [aws_acm_certificate.media]
}

resource "aws_cloudfront_origin_access_control" "media" {
  name                              = "${local.name}-media"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "media" {
  enabled     = true
  comment     = "${local.name} media"
  price_class = "PriceClass_200" # NA/EU/Asia (incl. India edge) — cheaper than All

  aliases = local.use_custom_domain ? [local.media_domain] : []

  origin {
    domain_name              = aws_s3_bucket.media.bucket_regional_domain_name
    origin_id                = "media-s3"
    origin_access_control_id = aws_cloudfront_origin_access_control.media.id
  }

  default_cache_behavior {
    target_origin_id       = "media-s3"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    # Managed "CachingOptimized" policy — long TTL (media keys are immutable UUIDs).
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6"
    # Managed "SecurityHeadersPolicy" — HSTS, nosniff, frame/referrer policies.
    response_headers_policy_id = "67f7725c-6f97-4210-82d7-5512b31e9d03"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  dynamic "viewer_certificate" {
    for_each = local.use_custom_domain ? [1] : []
    content {
      acm_certificate_arn = local.use_route53 ? (
        aws_acm_certificate_validation.media[0].certificate_arn
      ) : data.aws_acm_certificate.media_issued[0].arn
      ssl_support_method       = "sni-only"
      minimum_protocol_version = "TLSv1.2_2021"
    }
  }

  dynamic "viewer_certificate" {
    for_each = local.use_custom_domain ? [] : [1]
    content {
      cloudfront_default_certificate = true
    }
  }
}
