output "api_url" {
  value = "https://${local.api_domain}"
}

output "customer_portal_url" {
  value = "https://${local.customer_portal_domain}"
}

output "admin_portal_url" {
  value = "https://${local.admin_portal_domain}"
}

output "media_url" {
  value = local.media_url
}

output "api_elastic_ip" {
  description = "Point the API A-record here (done automatically if route53_zone_id is set)."
  value       = aws_eip.app.public_ip
}

output "cloudfront_domain" {
  description = "Point the media A/ALIAS record here (done automatically if route53_zone_id is set)."
  value       = aws_cloudfront_distribution.media.domain_name
}

output "media_bucket" {
  value = aws_s3_bucket.media.bucket
}

output "backups_bucket" {
  value = aws_s3_bucket.backups.bucket
}

output "ecr_backend_repo" {
  value = aws_ecr_repository.backend.repository_url
}

output "rds_endpoint" {
  value = aws_db_instance.main.address
}

output "jobs_queue_url" {
  value = aws_sqs_queue.jobs.url
}

output "manual_dns_records" {
  description = "Add these at Cloudflare (route53_zone_id empty). App must be DNS-only (grey cloud) so Caddy can get TLS."
  value = local.use_route53 ? "managed by Route53" : join("\n", concat(
    ["${local.api_domain}   A       ${aws_eip.app.public_ip}   [Proxy status: DNS only / grey cloud]"],
    local.use_custom_domain ? ["${local.media_domain}   CNAME   ${aws_cloudfront_distribution.media.domain_name}   [DNS only / grey cloud]"] : [],
  ))
}

# Add this CNAME at Cloudflare to validate the media ACM cert, THEN re-run `terraform apply`.
# Empty map when using Route53 (auto-validated) or the media domain is disabled.
output "acm_validation_record" {
  description = "CNAME(s) to add at Cloudflare for ACM validation (empty when not applicable)."
  value = {
    for dvo in((local.request_media_certificate && !local.use_route53) ? aws_acm_certificate.media[0].domain_validation_options : []) :
    dvo.domain_name => "${dvo.resource_record_name} CNAME ${dvo.resource_record_value}"
  }
}

output "media_domain_activation_required" {
  description = "For manual DNS: add acm_validation_record, wait for ISSUED, then set activate_media_domain=true and apply again."
  value       = local.request_media_certificate && !local.use_route53 && !var.activate_media_domain
}

output "ssh_command" {
  description = "SSH command template. Replace the identity-file path if a different local key was registered."
  value = var.ssh_ingress_cidr == "" ? null : (
    "ssh -i ~/.ssh/id_ed25519 ec2-user@${aws_eip.app.public_ip}"
  )
}

# ---- Local-dev S3 credentials (scoped to local/*) ---------------------------
output "local_dev_access_key_id" {
  value = one(aws_iam_access_key.local_dev[*].id)
}

output "local_dev_secret_access_key" {
  value     = one(aws_iam_access_key.local_dev[*].secret)
  sensitive = true
}
