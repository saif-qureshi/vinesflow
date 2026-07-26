terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  # Remote state (recommended — local state contains the DB password and JWT secret).
  # Bootstrap once, then uncomment and run `terraform init -migrate-state`:
  #   aws s3 mb s3://vineflow-tfstate --region ap-south-1
  #   aws s3api put-bucket-versioning --bucket vineflow-tfstate --versioning-configuration Status=Enabled
  # backend "s3" {
  #   bucket       = "vineflow-tfstate"
  #   key          = "prod/terraform.tfstate"
  #   region       = "ap-south-1"
  #   use_lockfile = true # S3-native locking (Terraform >= 1.10), no DynamoDB table needed
  #   encrypt      = true
  # }
}
