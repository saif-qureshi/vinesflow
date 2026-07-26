data "aws_ssm_parameter" "al2023_arm" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64"
}

resource "aws_instance" "app" {
  ami                    = data.aws_ssm_parameter.al2023_arm.value
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name
  key_name               = var.key_pair_name == "" ? null : var.key_pair_name

  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_gb
    encrypted   = true
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
    ecr_frontend    = aws_ecr_repository.frontend.repository_url
    app_domain      = local.app_domain
    swap_gb         = var.swap_gb
    backups_bucket  = aws_s3_bucket.backups.bucket
    db_host         = aws_db_instance.main.address
    db_name         = var.db_name
    db_user         = var.db_username
    compose_content = file("${path.module}/../docker/docker-compose.prod.yml")
  })

  # Re-run user_data if the env parameter or compose changes.
  user_data_replace_on_change = false

  tags = { Name = "${local.name}-app" }

  depends_on = [aws_db_instance.main]
}

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"
  tags     = { Name = "${local.name}-app" }
}
