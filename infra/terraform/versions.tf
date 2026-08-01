terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Bucket/key/region are supplied by infra/bootstrap-state.sh through backend.hcl.
  backend "s3" {
    encrypt      = true
    use_lockfile = true
  }
}
