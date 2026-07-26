terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  # Remote state (recommended). Create the bucket + DynamoDB table once, then uncomment.
  # backend "s3" {
  #   bucket         = "vineflow-tfstate"
  #   key            = "prod/terraform.tfstate"
  #   region         = "ap-south-1"
  #   dynamodb_table = "vineflow-tflock"
  #   encrypt        = true
  # }
}
