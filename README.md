# Vineflow

Multi-organization invoicing and inventory platform. A shared core — authentication, organizations, team members, role-based permissions, and an activity log — underpins the business modules (Items, Customers &amp; Vendors, Inventory, Sales, Purchases, Reports), which all plug into the same permission model.

## Stack

- **Backend** — FastAPI + SQLAlchemy 2.0 (sync, psycopg3) + Alembic, PostgreSQL. JWT access tokens + rotating, reuse-detecting refresh sessions delivered via httpOnly cookies. Uniform `{success, data, error}` response envelope. Typer management CLI.
- **Customer frontend** — Next.js (App Router) + Ant Design v6 + Tailwind 4, Zustand + TanStack Query, per-namespace types, and centralized theme tokens.
- **Super admin** — A separate Next.js application and session boundary for organization onboarding and platform oversight.

## Quick start

```bash
./dev.sh            # Postgres (Docker) + backend + frontend, one command
./dev.sh --seed     # also seed the permission catalog + demo account
```

- Customer frontend → http://localhost:3005
- Super admin → http://localhost:3010
- API docs → http://localhost:8005/docs
- Demo login → `admin@vineflow.app` / `password123`

> On this machine Postgres is mapped to host port **5433** (a local Postgres already holds 5432). Set `DB_HOST_PORT` to override.

## Layout

```
backend/          FastAPI app (app/modules/{auth,users,orgs,rbac,products,parties,...}), Alembic, CLI
frontend/         Next.js app (src/app, src/hooks, src/components, src/types, src/theme)
super-admin/      Separate Next.js super-administration app
docker-compose.yml  Postgres
dev.sh            run everything
```

## Backend CLI

```bash
cd backend
uv run vineflow users list
uv run vineflow users create --email you@co.com --password ... --org "Acme"
uv run vineflow super-admin create --email admin@vinesflow.com
uv run vineflow super-admin list
uv run vineflow orgs list
uv run vineflow roles list <org>
uv run vineflow db seed
uv run vineflow db prune-sessions
```

Super-admin credentials are never seeded. After migrations, run the `super-admin create`
command once and enter the password at its secure prompt.

## Authentication boundaries

Customer users and super administrators use separate database identities, access-token types, refresh-session tables, cookies, and login routes. Customer access cannot be used against super-admin APIs. Both use short-lived in-memory access JWTs and rotating, reuse-detecting httpOnly refresh cookies.

## RBAC

Users belong to multiple organizations via memberships; each membership has one org-scoped role. Roles map to a global `module:action` permission catalog. Every org is seeded with Super Admin / Admin / Member / Viewer; the org owner is Super Admin. UI and API are both gated by the current user's permissions in the active org (`X-Org-Id` header).
