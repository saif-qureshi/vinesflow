resource "aws_sns_topic" "alarms" {
  name = "${local.name}-alarms"
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/${local.name}/containers"
  retention_in_days = var.log_retention_days
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alarm_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# Route53 health-check metrics are published only in us-east-1, so their alarm
# and notification topic must live there even though the workload is in Mumbai.
resource "aws_sns_topic" "external_health" {
  count    = var.enable_external_health_check ? 1 : 0
  provider = aws.us_east_1
  name     = "${local.name}-external-health"
}

resource "aws_sns_topic_subscription" "external_health_email" {
  count     = var.enable_external_health_check && var.alarm_email != "" ? 1 : 0
  provider  = aws.us_east_1
  topic_arn = aws_sns_topic.external_health[0].arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# Host/hardware failure -> auto-recover migrates the instance to healthy hardware (free).
resource "aws_cloudwatch_metric_alarm" "ec2_system" {
  alarm_name          = "${local.name}-ec2-system-check"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed_System"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  alarm_actions       = ["arn:aws:automate:${var.region}:ec2:recover", aws_sns_topic.alarms.arn]
  dimensions          = { InstanceId = aws_instance.app.id }
}

# OS-level hang -> reboot.
resource "aws_cloudwatch_metric_alarm" "ec2_instance" {
  alarm_name          = "${local.name}-ec2-instance-check"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "StatusCheckFailed_Instance"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  alarm_actions       = ["arn:aws:automate:${var.region}:ec2:reboot", aws_sns_topic.alarms.arn]
  dimensions          = { InstanceId = aws_instance.app.id }
}

resource "aws_cloudwatch_metric_alarm" "ec2_cpu" {
  alarm_name          = "${local.name}-ec2-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions          = { InstanceId = aws_instance.app.id }
}

resource "aws_cloudwatch_metric_alarm" "ec2_memory" {
  alarm_name          = "${local.name}-ec2-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "mem_used_percent"
  namespace           = "Vineflow"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions          = { InstanceId = aws_instance.app.id }
}

resource "aws_cloudwatch_metric_alarm" "ec2_disk" {
  alarm_name          = "${local.name}-ec2-disk-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "disk_used_percent"
  namespace           = "Vineflow"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions          = { InstanceId = aws_instance.app.id }
}

resource "aws_route53_health_check" "app" {
  count             = var.enable_external_health_check ? 1 : 0
  fqdn              = local.api_domain
  port              = 443
  type              = "HTTPS"
  enable_sni        = true
  resource_path     = "/healthz"
  failure_threshold = 3
  request_interval  = 30

  tags = { Name = "${local.name}-app" }
}

resource "aws_cloudwatch_metric_alarm" "app_unavailable" {
  count               = var.enable_external_health_check ? 1 : 0
  provider            = aws.us_east_1
  alarm_name          = "${local.name}-app-unavailable"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HealthCheckStatus"
  namespace           = "AWS/Route53"
  period              = 60
  statistic           = "Minimum"
  threshold           = 1
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.external_health[0].arn]
  dimensions          = { HealthCheckId = aws_route53_health_check.app[0].id }
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${local.name}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions          = { DBInstanceIdentifier = aws_db_instance.main.identifier }
}

resource "aws_cloudwatch_metric_alarm" "rds_storage" {
  alarm_name          = "${local.name}-rds-low-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 2000000000 # 2 GB
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions          = { DBInstanceIdentifier = aws_db_instance.main.identifier }
}

resource "aws_cloudwatch_metric_alarm" "jobs_oldest" {
  alarm_name          = "${local.name}-jobs-oldest-message"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 600
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions          = { QueueName = aws_sqs_queue.jobs.name }
}

resource "aws_cloudwatch_metric_alarm" "jobs_dlq" {
  alarm_name          = "${local.name}-jobs-dlq-not-empty"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions          = { QueueName = aws_sqs_queue.jobs_dlq.name }
}

resource "aws_cloudwatch_metric_alarm" "backup_missing" {
  alarm_name          = "${local.name}-backup-missing"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "BackupSuccess"
  namespace           = "Vineflow"
  period              = 86400
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions          = { Project = local.name }
}

# Notification-only budgets are free.
resource "aws_budgets_budget" "monthly" {
  count        = var.alarm_email == "" ? 0 : 1
  name         = "${local.name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alarm_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alarm_email]
  }
}
