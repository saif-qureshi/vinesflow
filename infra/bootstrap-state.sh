#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="$SCRIPT_DIR/terraform"
STATE_REGION="${AWS_REGION:-ap-south-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
STATE_BUCKET="${TF_STATE_BUCKET:-vineflow-tfstate-$AWS_ACCOUNT_ID}"

if ! aws s3api head-bucket --bucket "$STATE_BUCKET" 2>/dev/null; then
  if [[ "$STATE_REGION" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "$STATE_BUCKET" --region "$STATE_REGION"
  else
    aws s3api create-bucket \
      --bucket "$STATE_BUCKET" \
      --region "$STATE_REGION" \
      --create-bucket-configuration "LocationConstraint=$STATE_REGION"
  fi
fi

aws s3api put-public-access-block \
  --bucket "$STATE_BUCKET" \
  --public-access-block-configuration \
  'BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true'
aws s3api put-bucket-versioning \
  --bucket "$STATE_BUCKET" \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption \
  --bucket "$STATE_BUCKET" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-bucket-lifecycle-configuration \
  --bucket "$STATE_BUCKET" \
  --lifecycle-configuration \
  '{"Rules":[{"ID":"expire-old-state-versions","Status":"Enabled","Filter":{},"NoncurrentVersionExpiration":{"NoncurrentDays":90},"AbortIncompleteMultipartUpload":{"DaysAfterInitiation":7}}]}'

umask 077
cat > "$TF_DIR/backend.hcl" <<BACKEND_EOF
bucket = "$STATE_BUCKET"
key    = "prod/terraform.tfstate"
region = "$STATE_REGION"
BACKEND_EOF

terraform -chdir="$TF_DIR" init -migrate-state -force-copy -backend-config=backend.hcl
echo "Remote Terraform state is ready in s3://$STATE_BUCKET/prod/terraform.tfstate"
