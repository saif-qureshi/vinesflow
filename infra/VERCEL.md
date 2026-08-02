# Vercel production setup

Use one Vercel Pro team with separate projects so each portal has independent deployments and
domains. The repository's AWS workflow deploys only the API stack.

| Vercel project | Root directory | Production domain | Production environment |
|---|---|---|---|
| Customer portal | `frontend` | `app.vinesflow.com` | `NEXT_PUBLIC_API_URL=https://api.vinesflow.com/api/v1` |
| Super admin | `super-admin` | `admin.vinesflow.com` | `NEXT_PUBLIC_API_URL=https://api.vinesflow.com/api/v1` |
| Marketing | existing marketing project/repository | `vinesflow.com`, `www.vinesflow.com` | project-specific |

The current repository does not contain a dedicated marketing application. Keep the existing
marketing Vercel project attached to the apex and `www` domains.

## Setup

1. Import this GitHub repository twice in Vercel.
2. Set the Root Directory to `frontend` for the customer project and `super-admin` for admin.
3. Add the Production environment variable shown above to both projects.
4. Deploy `main` and confirm each generated `*.vercel.app` deployment works.
5. Add the custom domain to its project.
6. In Cloudflare, add the exact CNAME Vercel requests with proxying disabled.
7. Enable deployment protection for preview deployments, especially super-admin.
8. Set a Vercel spend limit and notifications before enabling production traffic.

The API uses credentialed CORS for exactly `https://app.vinesflow.com` and
`https://admin.vinesflow.com`. Authentication cookies remain host-only to `api.vinesflow.com` and
both clients already send credentialed API requests.
