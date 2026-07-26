# Vineflow — Production Infrastructure (AWS, cost-optimized)

Single-region deployment tuned for a Pakistan operation. One Graviton EC2 runs the whole
stack behind Caddy (auto-TLS); Postgres is managed by RDS; media is served privately via
CloudFront. No ALB, no NAT gateway, no per-tenant IAM — the usual budget-killers are avoided.

**Region:** `ap-south-1` (Mumbai) — cheapest low-latency region for Pakistan (AWS has none in-country).

```
Internet ── app.<domain> ─────────────► EC2 t4g.small (ARM)
                                          Docker Compose:
                                            Caddy (TLS, proxy) · frontend (Next.js)
                                            backend (FastAPI) · gotenberg · autoheal
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
- **Auto-recovery:** every container is `restart: always`; a `vineflow.service` systemd unit
  brings the stack up on boot; an `autoheal` container restarts anything that goes *unhealthy*.
- **TLS:** Caddy provisions Let's Encrypt automatically for `app.<domain>`.
- **Backups:** RDS automated backups + PITR (14 days) **and** a nightly logical `pg_dump` → S3
  (14-day lifecycle).
- **Secrets:** the whole backend `.env` lives in one SSM SecureString, pulled at boot. No keys on disk in git.
  `.dockerignore` keeps `backend/.env` out of image layers.
- **Alerts:** CloudWatch alarms (EC2 status/CPU, RDS CPU/storage) → SNS email (`alarm_email`), plus an
  AWS Budgets alert at 80% actual / 100% forecasted of `monthly_budget_usd`.
- **Self-healing:** system status-check failure auto-recovers the instance to healthy hardware;
  instance status-check failure auto-reboots. Both free.
- **Hardening:** IMDSv2-only, private RDS (TLS forced by default on Postgres 15+), non-root app
  containers, HSTS/nosniff/frame headers at Caddy and CloudFront, OIDC deploys (no static AWS keys).

## Prerequisites
- Terraform ≥ 1.6, AWS CLI, an AWS account, a registered domain.
- Docker (to build/push images).
- Ideally the domain in **Route53** (`route53_zone_id`) for fully automated DNS + TLS. Without it,
  Terraform prints the records to add manually (`manual_dns_records`) and you validate the media
  ACM cert by hand.

## Deploy

**1) Provision infra**
```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # set domain_name (+ route53_zone_id, github_repo)
terraform init && terraform apply
```
The instance boots and configures itself, but ECR is empty on the first apply — so the app
containers come up only after the first image push (step 2).

**2) CI/CD (recommended) — GitHub Actions, OIDC, no static keys**

Set `github_repo` in `terraform.tfvars` and re-`apply`, then in GitHub →
*Settings → Secrets and variables → Actions → Variables*, add the values Terraform prints:
```bash
terraform output github_actions_setup
# -> AWS_ROLE_ARN, AWS_REGION, ECR_BACKEND, ECR_FRONTEND, INSTANCE_ID
```
Now `.github/workflows/deploy.yml` runs on every push to `main` (or via *Run workflow*): it builds
both ARM64 images, pushes `:latest` + `:<sha>` to ECR, and rolls the instance over SSM (`docker
compose pull && up`). Fully hands-off after setup.

**Manual deploy (fallback, no CI)**
```bash
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin "$(terraform output -raw ecr_backend_repo | cut -d/ -f1)"
docker buildx build --platform linux/arm64 -f infra/docker/backend.Dockerfile  -t "$(terraform output -raw ecr_backend_repo):latest"  --push ../backend
docker buildx build --platform linux/arm64 -f infra/docker/frontend.Dockerfile -t "$(terraform output -raw ecr_frontend_repo):latest" --push ../frontend
# then, via SSM Session Manager on the instance:
sudo systemctl restart vineflow.service
```

DNS (if not using Route53): point `app.<domain>` → `app_elastic_ip`, and `media.<domain>` →
`cloudfront_domain` (see `terraform output`).

## Local dev against S3 (the `local/` prefix)
The media bucket has a dedicated **`local/`** prefix reachable only by a scoped IAM user:

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

## Backup / restore
- Automated: RDS snapshots + PITR (restore from the RDS console).
- Logical: `s3://<backups_bucket>/db/…sql.gz` nightly. Restore:
  ```bash
  gunzip -c dump.sql.gz | PGPASSWORD=… psql -h <rds-endpoint> -U vineflow -d vineflow
  ```

## Scaling up (when traffic justifies it — additive, not a rebuild)
1. **Background jobs:** uncomment `redis` + `worker` in `docker-compose.prod.yml`; bump `instance_type` to `t4g.medium`+.
2. **HA:** flip `db_multi_az = true`, add an ALB + a second instance behind it.
3. **DB headroom:** `db_instance_class = "db.t4g.small"`.

## Files
```
infra/
  terraform/   network · security · iam · ecr · s3 · cloudfront · rds · ssm · compute · monitoring · dns · outputs
  docker/      backend.Dockerfile · frontend.Dockerfile · docker-compose.prod.yml · Caddyfile · backend.env.example
```
