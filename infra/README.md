# Vineflow — Production Infrastructure (AWS, cost-optimized)

Single-region deployment tuned for a Pakistan operation. One Graviton EC2 runs the whole
stack behind Caddy (auto-TLS); Postgres is managed by RDS; media is stored in a private S3
bucket and delivered as public bearer URLs through CloudFront. No ALB or NAT gateway is used.

**Region:** `ap-south-1` (Mumbai) — cheapest low-latency region for Pakistan (AWS has none in-country).

```
Internet ── app.<domain> ─────────────► EC2 t4g.small (ARM)
                                          Docker Compose:
                                            Caddy (TLS, proxy) · frontend (Next.js)
                                            backend (FastAPI) · worker · gotenberg
                                          IAM role (no keys)
             media.<domain> ─► CloudFront ─► S3 media (private, OAC)   ── writes ── EC2
                                          RDS Postgres (private subnets, SG-locked)
                                          S3 backups · SSM params · ECR
```

## Monthly cost (Lean tier, low traffic)

| Item | Spec | ~$/mo |
|---|---|---|
| EC2 | t4g.small (2 GB, Graviton) | ~$12 |
| RDS | db.t4g.micro, single-AZ, 20 GB | ~$15 |
| EBS | gp3 30 GB | ~$2.4 |
| Public IPv4 | Elastic IP ($0.005/hr) | ~$3.7 |
| S3 + CloudFront + transfer | low volume | ~$3–5 |
| ECR | last 10 images | ~$0.20 |
| **Total** | | **~$37–40** |

More headroom: `t4g.medium` (4 GB) adds ~$12/mo. Once sizes are stable, a 1-yr no-upfront
Compute Savings Plan (~40% off EC2) plus an RDS Reserved Instance (~35% off) lands around
**$28–32/mo**. With ~$1000 in credits the Lean tier lasts ~2 years.

## What you get
- **Auto-recovery:** every container is `restart: always`, and a `vineflow.service` systemd unit
  brings the stack up on boot. No container receives access to the Docker socket.
- **TLS:** Caddy provisions Let's Encrypt automatically for `app.<domain>`.
- **Backups:** RDS automated backups + PITR (14 days) **and** a nightly logical `pg_dump` → S3
  (14-day lifecycle).
- **Secrets:** the whole backend `.env` lives in one SSM SecureString and is refreshed at boot and
  before every deploy. No keys are stored in Git.
  `.dockerignore` keeps `backend/.env` out of image layers.
- **Alerts:** CloudWatch alarms cover EC2/RDS health, stale SQS jobs, DLQ messages, and missing
  nightly backups → SNS email (`alarm_email`), plus AWS Budgets alerts.
- **Self-healing:** system status-check failure auto-recovers the instance to healthy hardware;
  instance status-check failure auto-reboots. Both free.
- **Hardening:** IMDSv2-only, private RDS (TLS forced by default on Postgres 15+), non-root app
  containers, HSTS/nosniff/frame headers at Caddy and CloudFront, OIDC deploys (no static AWS keys).

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
This creates `vineflow-tfstate-<account-id>`, blocks public access, enables encryption and
versioning, writes ignored `infra/terraform/backend.hcl`, and initializes S3-native locking.

**2) Provision infra**
```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # set domain_name (+ route53_zone_id, github_repo)
terraform apply
```
The instance boots and configures itself, but ECR is empty on the first apply — so the app
containers come up only after the first image push.

**3) CI/CD (recommended) — GitHub Actions, OIDC, no static keys**

Set `github_repo` in `terraform.tfvars` and re-`apply`, then in GitHub →
*Settings → Secrets and variables → Actions → Variables*, add the values Terraform prints:
```bash
terraform output github_actions_setup
# -> AWS_ROLE_ARN, AWS_REGION, ECR_BACKEND, ECR_FRONTEND, INSTANCE_ID, SSM_ENV_PARAM
```
Now `.github/workflows/deploy.yml` runs on every push to `main`: it builds both ARM64 images,
stages Compose/Caddy, refreshes SSM secrets, deploys the immutable commit SHA, waits for readiness,
and restores the prior configuration on failure. OIDC is restricted to the `main` branch.

**Manual deploy (fallback, no CI)**
```bash
cd ../.. # repository root, if you are still in infra/terraform
SHA=$(git rev-parse HEAD)
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin \
  "$(terraform -chdir=infra/terraform output -raw ecr_backend_repo | cut -d/ -f1)"
docker buildx build --platform linux/arm64 -f infra/docker/backend.Dockerfile \
  -t "$(terraform -chdir=infra/terraform output -raw ecr_backend_repo):$SHA" --push backend
docker buildx build --platform linux/arm64 -f infra/docker/frontend.Dockerfile \
  -t "$(terraform -chdir=infra/terraform output -raw ecr_frontend_repo):$SHA" --push frontend
# Stage docker-compose.yml.next and Caddyfile.next on the instance, then run:
sudo /opt/vineflow/deploy.sh "$SHA"
```

DNS (if not using Route53): point `app.<domain>` → `app_elastic_ip`, and `media.<domain>` →
`cloudfront_domain` (see `terraform output`).

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
1. **Background jobs:** the SQS worker is already enabled; bump `instance_type` to `t4g.medium`+
   as job volume or concurrency grows.
2. **HA:** flip `db_multi_az = true`, add an ALB + a second instance behind it.
3. **DB headroom:** `db_instance_class = "db.t4g.small"`.

## Files
```
infra/
  terraform/   network · security · iam · ecr · s3 · cloudfront · rds · ssm · compute · monitoring · dns · outputs
  docker/      Dockerfiles · Compose · Caddyfile · transactional deploy script
```
