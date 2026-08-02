# GitHub Actions deploys via OIDC (no static AWS keys stored in GitHub).
# Set github_repo to enable; leave empty to skip all CI/CD resources.

variable "github_repo" {
  description = "owner/repo allowed to assume the deploy role, e.g. saif-qureshi/vinesflow"
  type        = string
  default     = ""
}

variable "github_oidc_provider_arn" {
  description = "Existing GitHub OIDC provider ARN in this account. Leave empty to create one."
  type        = string
  default     = ""
}

locals {
  enable_cicd = var.github_repo != ""
  create_oidc = local.enable_cicd && var.github_oidc_provider_arn == ""
  oidc_arn    = local.create_oidc ? aws_iam_openid_connect_provider.github[0].arn : var.github_oidc_provider_arn
}

resource "aws_iam_openid_connect_provider" "github" {
  count           = local.create_oidc ? 1 : 0
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

data "aws_iam_policy_document" "gha_assume" {
  count = local.enable_cicd ? 1 : 0
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.oidc_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "gha_deploy" {
  count              = local.enable_cicd ? 1 : 0
  name               = "${local.name}-gha-deploy"
  assume_role_policy = data.aws_iam_policy_document.gha_assume[0].json
}

data "aws_iam_policy_document" "gha_deploy" {
  count = local.enable_cicd ? 1 : 0

  statement {
    sid       = "EcrAuth"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid = "EcrPush"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [aws_ecr_repository.backend.arn]
  }

  statement {
    sid     = "SsmDeploy"
    actions = ["ssm:SendCommand"]
    resources = [
      "arn:aws:ec2:${var.region}:${data.aws_caller_identity.current.account_id}:instance/${aws_instance.app.id}",
      "arn:aws:ssm:${var.region}::document/AWS-RunShellScript",
    ]
  }

  statement {
    sid       = "SsmStatus"
    actions   = ["ssm:GetCommandInvocation", "ssm:ListCommands", "ssm:ListCommandInvocations"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "gha_deploy" {
  count  = local.enable_cicd ? 1 : 0
  name   = "deploy"
  role   = aws_iam_role.gha_deploy[0].id
  policy = data.aws_iam_policy_document.gha_deploy[0].json
}

# ---- Convenience: the exact GitHub Actions *variables* to set (from `terraform output`) ----
# AWS_ROLE_ARN is null when github_repo is unset (CI/CD disabled).
output "github_actions_setup" {
  description = "Set these as repo Variables (Settings -> Secrets and variables -> Actions -> Variables)."
  value = {
    AWS_ROLE_ARN  = one(aws_iam_role.gha_deploy[*].arn)
    AWS_REGION    = var.region
    ECR_BACKEND   = aws_ecr_repository.backend.repository_url
    INSTANCE_ID   = aws_instance.app.id
    SSM_ENV_PARAM = aws_ssm_parameter.backend_env.name
  }
}
