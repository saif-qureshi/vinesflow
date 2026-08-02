# Vineflow super-admin portal

Next.js internal administration portal deployed to Vercel at `admin.vinesflow.com`.

## Local development

```bash
cp .env.example .env.local
pnpm install --frozen-lockfile
pnpm dev
```

## Vercel

Create a separate Vercel project from this repository with `super-admin` as its Root Directory.
Set this Production environment variable:

```text
NEXT_PUBLIC_API_URL=https://api.vinesflow.com/api/v1
```

Assign `admin.vinesflow.com`. Keep Vercel deployment protection enabled for previews so the admin
interface is not exposed from preview URLs.
