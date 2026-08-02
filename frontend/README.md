# Vineflow customer portal

Next.js customer portal deployed to Vercel at `app.vinesflow.com`.

## Local development

```bash
cp .env.example .env.local
pnpm install --frozen-lockfile
pnpm dev
```

## Vercel

Create a Vercel project from this repository with `frontend` as its Root Directory. Set this
Production environment variable:

```text
NEXT_PUBLIC_API_URL=https://api.vinesflow.com/api/v1
```

Assign `app.vinesflow.com` after the AWS API is healthy. Preview deployments should use an API URL
appropriate for their environment rather than production customer data.
