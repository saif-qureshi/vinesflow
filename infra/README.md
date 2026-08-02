# Vineflow — Production Infrastructure (AWS, cost-optimized)

Single-region AWS backend tuned for a Pakistan operation. Vercel serves the customer, admin, and
marketing frontends. One Graviton EC2 runs the API/worker/PDF stack behind Caddy; Postgres is
managed by RDS; media is stored in private S3 and delivered through CloudFront. No ALB or NAT
gateway is used.

**Region:** `ap-south-1` (Mumbai) — cheapest low-latency region for Pakistan (AWS has none in-country).

```
Internet ── api.<domain> ─────────────► EC2 t4g.medium (ARM)
                                          Docker Compose:
                                            Caddy (TLS, proxy) · backend (FastAPI)
                                            worker · migration job · gotenberg
                                          IAM role (no keys)
             app.<domain> ─────────────► Vercel customer portal
           admin.<domain> ─────────────► Vercel super-admin portal
     <domain> / www.<domain> ──────────► Vercel marketing site
             media.<domain> ─► CloudFront ─► S3 media (private, OAC)   ── writes ── EC2
                                          RDS Postgres (private subnets, SG-locked)
                                          S3 backups · SSM params · ECR
```

## Monthly cost (production tier, low traffic)

| Item | Spec | ~$/mo |
|---|---|---|
| EC2 | t4g.medium (4 GB, Graviton) | ~$16.35 |
| RDS | db.t4g.micro, single-AZ | ~$15.33 |
| EBS | gp3 30 GB | ~$2.74 |
| RDS storage | gp3 20 GB | ~$2.62 |
| Public IPv4 | Elastic IP ($0.005/hr) | ~$3.7 |
| S3 + ECR + alarms | low volume | ~$1–3 |
| CloudFront + transfer | within low-traffic free allowances | ~$0 |
| **Total** | | **~$41–45** |

The estimate excludes taxes, unusually heavy traffic, and sustained T-family CPU surplus charges.
`monthly_budget_usd = 75` leaves operational headroom while still catching unexpected spend.

## What you get
- **Auto-recovery:** every container is `restart: always`, and a `vineflow.service` systemd unit
  brings the stack up on boot. No container receives access to the Docker socket.
- **TLS:** Caddy provisions Let's Encrypt automatically for `api.<domain>`; Vercel manages frontend TLS.
- **Frontends:** Vercel deploys `frontend/` to `app.<domain>` and `super-admin/` to
  `admin.<domain>` independently from the AWS backend.
- **Backups:** RDS automated backups + PITR (14 days) **and** a nightly logical `pg_dump` → S3
  (14-day lifecycle). Every deploy also takes a pre-migration logical backup.
- **Secrets:** the whole backend `.env` lives in one SSM SecureString and is refreshed at boot and
  before every deploy. No keys are stored in Git.
  `.dockerignore` keeps `backend/.env` out of image layers.
- **Alerts:** CloudWatch alarms cover external HTTPS availability, EC2 CPU/memory/disk, RDS health,
  stale SQS jobs, DLQ messages, and missing backups → SNS email, plus AWS Budgets alerts.
- **Logs:** container and Caddy access logs are retained in CloudWatch Logs for 30 days.
- **Self-healing:** system status-check failure auto-recovers the instance to healthy hardware;
  instance status-check failure auto-reboots. Both free.
- **Hardening:** IMDSv2-only with metadata access limited to the AWS-aware container network,
  private RDS with forced TLS, encrypted S3 with TLS-only bucket policies, non-root app containers,
  immutable ECR tags, security headers, and OIDC deploys with no static AWS keys.

## Prerequisites
- Terraform ≥ 1.10, AWS CLI, an AWS account, a registered domain.
- Docker (to build/push images).
- Ideally the domain in **Route53** (`route53_zone_id`) for fully automated DNS + TLS. Without it,
  Terraform prints the records to add manually (`manual_dns_records`) and you validate the media
  ACM cert by hand.

## Deploy

**1) Bootstrap encrypted, versioned remote state (once per AWS account)**
```bash
./infra/bootstrap-state.sh
```
This creates `vinesflow-tfstate-<account-id>`, blocks public access, enables encryption and
versioning, writes ignored `infra/terraform/backend.hcl`, and initializes S3-native locking.

**2) First apply**
```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # set domain_name (+ route53_zone_id, github_repo)
terraform apply
```
With Route53, this provisions everything. With manual DNS such as Cloudflare, the first apply
creates a working default CloudFront distribution and prints `acm_validation_record` without
blocking on certificate validation:
```bash
terraform output -json acm_validation_record
```
Add the exact CNAME at Cloudflare with proxying disabled. After ACM reports `ISSUED`, set
`activate_media_domain = true` and apply again. Terraform refuses activation until an issued
certificate exists. The app containers start only after the first image push because ECR begins empty.

**3) CI/CD (recommended) — GitHub Actions, OIDC, no static keys**

Set `github_repo` in `terraform.tfvars` and re-`apply`, then in GitHub →
*Settings → Secrets and variables → Actions → Variables*, add the values Terraform prints:
```bash
terraform output github_actions_setup
# -> AWS_ROLE_ARN, AWS_REGION, ECR_BACKEND, INSTANCE_ID, SSM_ENV_PARAM
```
Now `.github/workflows/deploy.yml` runs on backend/infrastructure pushes to `main`: it builds the
ARM64 backend image, stages Compose/Caddy, refreshes SSM secrets, deploys the immutable commit SHA,
waits for readiness, and restores the prior configuration on failure. OIDC is restricted to main.
Database migrations run as a dedicated dependency before the app is replaced; migrations must use
expand/contract compatibility because an application rollback does not reverse an applied schema.

Vercel deploys the customer and admin portals through its Git integration. See `infra/VERCEL.md`.

**Manual deploy (fallback, no CI)**
```bash
cd ../.. # repository root, if you are still in infra/terraform
SHA=$(git rev-parse HEAD)
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin \
  "$(terraform -chdir=infra/terraform output -raw ecr_backend_repo | cut -d/ -f1)"
docker buildx build --platform linux/arm64 -f infra/docker/backend.Dockerfile \
  -t "$(terraform -chdir=infra/terraform output -raw ecr_backend_repo):$SHA" --push backend
# Stage docker-compose.yml.next and Caddyfile.next on the instance, then run:
sudo /opt/vineflow/deploy.sh "$SHA"
```

DNS (if not using Route53): point `api.<domain>` → `api_elastic_ip`, and `media.<domain>` →
`cloudfront_domain` (see `terraform output`).

SSH stays enabled only when both a `/32` `ssh_ingress_cidr` and either `ssh_public_key` or an existing
`key_pair_name` are configured. SSM Session Manager remains the recovery access path.

## Local dev against S3 (the `local/` prefix)
The media bucket can expose a dedicated **`local/`** prefix through an optional scoped IAM user.
Set `enable_local_dev_credentials = true`, apply, and retrieve the credentials:

```bash
terraform output local_dev_access_key_id
terraform output -raw local_dev_secret_access_key
```

In your local `backend/.env`:
```
STORAGE_BACKEND=s3
S3_BUCKET=<terraform output media_bucket>
S3_REGION=ap-south-1
S3_PUBLIC_URL=<terraform output media_url>
MEDIA_KEY_PREFIX=local/          # dev objects go under local/ ; prod uses "" (org-*)
AWS_ACCESS_KEY_ID=<local_dev_access_key_id>
AWS_SECRET_ACCESS_KEY=<local_dev_secret_access_key>
```
Prod (the EC2 role) can read/write every `org-*` object but **not** `local/*`; the local user can
touch **only** `local/*`.

> Media privacy: S3 itself is private, but CloudFront object URLs are bearer-public. UUID object
> keys make them difficult to guess, but this is not authorization. If uploads must be confidential,
> add signed CloudFront URLs/cookies and issue them only through authenticated API responses.

## Backup / restore
- Automated: RDS snapshots + PITR (restore from the RDS console).
- Logical: `s3://<backups_bucket>/db/…sql.gz` nightly. Restore:
  ```bash
  gunzip -c dump.sql.gz | PGPASSWORD=… psql -h <rds-endpoint> -U vineflow -d vineflow
  ```

## Scaling up (when traffic justifies it — additive, not a rebuild)
1. **Background jobs:** the SQS worker is already enabled; bump `instance_type` above `t4g.medium`
   as job volume or concurrency grows.
2. **HA:** flip `db_multi_az = true`, add an ALB + a second instance behind it.
3. **DB headroom:** `db_instance_class = "db.t4g.small"`.

## Files
```
infra/
  terraform/   network · security · iam · ecr · s3 · cloudfront · rds · ssm · compute · monitoring · dns · outputs
  docker/      backend Dockerfile · Compose · Caddyfile · transactional deploy script
  VERCEL.md    customer/admin/marketing domain and project setup
```
