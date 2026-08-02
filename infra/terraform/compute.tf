data "aws_ssm_parameter" "al2023_arm" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64"
}

resource "aws_key_pair" "app" {
  count      = trimspace(var.ssh_public_key) == "" ? 0 : 1
  key_name   = "${local.name}-ssh"
  public_key = trimspace(var.ssh_public_key)

  tags = { Name = "${local.name}-ssh" }
}

resource "aws_instance" "app" {
  ami                    = var.ami_id == "" ? data.aws_ssm_parameter.al2023_arm.value : var.ami_id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name
  key_name = trimspace(var.ssh_public_key) != "" ? aws_key_pair.app[0].key_name : (
    var.key_pair_name == "" ? null : var.key_pair_name
  )

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_gb
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_tokens                 = "required" # IMDSv2 only
    http_put_response_hop_limit = 2          # Docker bridge adds a hop; containers need role creds
  }

  user_data = templatefile("${path.module}/templates/user_data.sh.tftpl", {
    region          = var.region
    project_name    = local.name
    ssm_env_param   = aws_ssm_parameter.backend_env.name
    ecr_backend     = aws_ecr_repository.backend.repository_url
    api_domain      = local.api_domain
    swap_gb         = var.swap_gb
    backups_bucket  = aws_s3_bucket.backups.bucket
    db_host         = aws_db_instance.main.address
    db_name         = var.db_name
    db_user         = var.db_username
    compose_version = var.docker_compose_version
    compose_content = file("${path.module}/../docker/docker-compose.prod.yml")
    caddy_content   = file("${path.module}/../docker/Caddyfile")
    deploy_script   = file("${path.module}/../docker/deploy.sh")
    log_group_name  = aws_cloudwatch_log_group.app.name
  })

  # Cloud-init is for first boot. Existing hosts receive config and secrets through deploy.sh.
  user_data_replace_on_change = false

  tags = { Name = "${local.name}-app" }

  lifecycle {
    # Cloud-init is first-boot configuration. Runtime files are updated through
    # the deployment workflow, so later template edits must not stop the host.
    ignore_changes = [user_data]

    precondition {
      condition     = !(trimspace(var.ssh_public_key) != "" && var.key_pair_name != "")
      error_message = "Set either ssh_public_key or key_pair_name, not both."
    }
    precondition {
      condition     = var.ssh_ingress_cidr == "" || trimspace(var.ssh_public_key) != "" || var.key_pair_name != ""
      error_message = "SSH ingress requires ssh_public_key or key_pair_name."
    }
  }

  depends_on = [aws_db_instance.main]
}

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"
  tags     = { Name = "${local.name}-app" }
}
