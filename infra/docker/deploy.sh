#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=/opt/vineflow
NEW_TAG="${1:?usage: deploy.sh <immutable-image-tag> [ssm-env-parameter]}"
SSM_ENV_OVERRIDE="${2:-}"

cd "$ROOT"

if ! [[ "$NEW_TAG" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Refusing non-commit image tag: $NEW_TAG" >&2
  exit 2
fi

exec 9>"$ROOT/deploy.lock"
flock -n 9 || {
  echo "Another deployment is already running" >&2
  exit 3
}

for staged in docker-compose.yml.next Caddyfile.next; do
  test -s "$staged"
done

SSM_ENV_PARAM=$(awk -F= '$1 == "SSM_ENV_PARAM" { print substr($0, index($0, "=") + 1) }' deploy.env)
AWS_REGION=$(awk -F= '$1 == "AWS_REGION" { print substr($0, index($0, "=") + 1) }' deploy.env)
if [[ -n "$SSM_ENV_OVERRIDE" ]]; then
  SSM_ENV_PARAM="$SSM_ENV_OVERRIDE"
fi
test -n "$SSM_ENV_PARAM"
test -n "$AWS_REGION"

aws ssm get-parameter --with-decryption --region "$AWS_REGION" \
  --name "$SSM_ENV_PARAM" --query 'Parameter.Value' --output text > backend.env.next
test -s backend.env.next
chmod 600 backend.env.next

awk -F= -v tag="$NEW_TAG" -v ssm="$SSM_ENV_PARAM" '
  BEGIN { tag_replaced = 0; ssm_replaced = 0 }
  $1 == "IMAGE_TAG" { print "IMAGE_TAG=" tag; tag_replaced = 1; next }
  $1 == "SSM_ENV_PARAM" { print "SSM_ENV_PARAM=" ssm; ssm_replaced = 1; next }
  { print }
  END {
    if (!tag_replaced) print "IMAGE_TAG=" tag
    if (!ssm_replaced) print "SSM_ENV_PARAM=" ssm
  }
' deploy.env > deploy.env.next

cp docker-compose.yml docker-compose.yml.rollback
cp Caddyfile Caddyfile.rollback
cp backend.env backend.env.rollback

rollback() {
  status=$?
  echo "Deployment failed; restoring the previous configuration" >&2
  mv -f docker-compose.yml.rollback docker-compose.yml
  mv -f Caddyfile.rollback Caddyfile
  mv -f backend.env.rollback backend.env
  docker compose --env-file deploy.env up -d --remove-orphans || true
  exit "$status"
}
trap rollback ERR

mv docker-compose.yml.next docker-compose.yml
mv Caddyfile.next Caddyfile
mv backend.env.next backend.env

docker compose --env-file deploy.env.next config -q
"$ROOT/ecr-login.sh"
docker compose --env-file deploy.env.next pull
docker compose --env-file deploy.env.next up -d --remove-orphans --wait --wait-timeout 180
docker compose --env-file deploy.env.next exec -T backend curl -fsS http://localhost:8000/ready

mv deploy.env.next deploy.env
rm -f docker-compose.yml.rollback Caddyfile.rollback backend.env.rollback
trap - ERR

docker image prune -f
echo "Deployment of $NEW_TAG completed successfully"
