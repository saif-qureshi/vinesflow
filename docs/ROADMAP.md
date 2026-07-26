# Vineflow Product Roadmap

Status: **directional**. This is the north-star roadmap, not a commitment. It is
organized on two axes — **surfaces** (where users touch Vineflow) and **products**
(what it does) — plus the **platform capabilities** and **compliance** that cut
across both. Sequencing follows one rule from day one: **finish the shared core
first, then widen surfaces, then add products.**

## Vision

One business platform for Pakistani SMBs: a **shared core** (organizations, RBAC,
parties, products, documents, payments, and the accounting ledger) with many
**products** layered on top — Invoicing, Inventory, Books, and Booking next.
Built **FBR-compliant** and **accounting-ready** from the ground up so nothing
needs reshaping as products are added. See `docs/vineflow-*` and the module plans
referenced below.

---

## Where we are today (shipped)

- **Web app** (Next.js 16 / Ant Design v6): auth + multi-tenant orgs + RBAC.
- **Sales:** sales orders → delivery challans → invoices → sales receipts.
- **Purchases:** purchase orders → goods receipts → bills.
- **Payments** in/out with allocation lifecycle; **credit/debit notes**.
- **Inventory:** products + variants, stock levels, movements, adjustments,
  transfers, multi-location.
- **FBR Digital Invoicing** (sandbox + production, IRN/QR).
- **Dashboard** (real KPIs), **media on S3/CloudFront**.
- **Production infra:** AWS (Terraform) + GitHub CI/CD, Pakistan region.

Refs: `docs/invoicing-fbr-plan.md`, `docs/advanced-inventory-plan.md`,
`docs/payments-and-accounting-plan.md`, `docs/books-accounting-plan.md`,
`infra/README.md`.

---

## Horizon 1 — Now (finish the financial loop, then launch)

The core isn't "done" until money is fully accounted for and the app can talk to
its users.

- **Books / Accounting GL** — B0–B7 in `docs/books-accounting-plan.md` (chart of
  accounts, ledger engine, auto-posting, expenses, reports, period close).
- **Expenses** capture (part of B3) — also unblocks the dashboard net-profit figure.
- **Email / notification layer** — password reset, teammate invites, "email this
  invoice", payment reminders (deferred earlier; a launch blocker). A shared
  `notifications` table also carries **low-stock alerts** (Advanced Inventory W1).
- **Reporting** — financial (P&L, Balance Sheet, Cash Flow, TB, GL) + operational
  (sales, purchases, inventory, aging).
- **Onboarding polish** — the org seeder is complete; add a first-run setup wizard.

**Exit:** a new business can sign up, sell, buy, get paid, stay FBR-compliant, and
see correct books — end to end, on the web.

---

## Horizon 2 — Next (widen the surfaces)

Same backend, new front doors. This is where **mobile / desktop / POS** live.

| Surface | What it's for | Tech direction |
|---|---|---|
| **Mobile app** (iOS + Android) | Invoicing on the go · **expense capture with receipt-photo OCR** · barcode stock lookup & counts · dashboards · approvals · push notifications | React Native / Expo (shares TS types with web) |
| **Desktop app** (Windows + Mac) | **POS / counter billing**, offline-first, thermal receipt + barcode/label printing, cash-drawer/scanner support | Tauri (small, native, wraps the web core) |
| **POS module** | Fast retail checkout: scan, tender, print, sync — feeds the same inventory + ledger | Web + desktop shell |
| **WhatsApp** | Send invoices, receipts, and payment reminders; the default channel in Pakistan | WhatsApp Business API |
| **Customer / Vendor portal** | Self-service: view invoices/statements, download, **pay online** | Public routes on the web app |
| **Payment gateways** | "Pay Now" on invoices → JazzCash, Easypaisa, bank/PayFast (local); Stripe (international) | Records straight into Payments/GL |
| **Public API + webhooks** | Integrations, custom apps, automation (Zapier/Make) | Versioned REST + tokens |

**Advanced Inventory — Wave 1 (pairs with mobile/desktop):** **barcode scanning**
(keyboard-wedge + camera), **stock-take / cycle-count**, and **bins / shelf
sub-locations** — the warehouse operations that only pay off once there's a
scanner in hand. See `docs/advanced-inventory-plan.md`.

**Exit:** users transact from phone, counter, and web; customers can pay online;
Vineflow is reachable programmatically; the warehouse can scan and count.

---

## Horizon 3 — Later (new products & depth)

New verticals on the shared core, and depth where power users need it.

- **Booking** — the platform's next product (appointments / reservations /
  services), reusing parties, documents, payments, and the ledger.
- **Manufacturing / BOM** — assemblies, work orders, consumption → COGS.
- **HR & Payroll** — Pakistan payroll (salary, EOBI, income tax, payslips).
- **CRM** — leads → quotations → customers; pipeline.
- **Projects & timesheets** — billable time → invoices.
- **Bank feeds & reconciliation** — import statements, match to ledger.
- **E-commerce connectors** — Shopify / WooCommerce / Daraz (orders + stock sync).
- **Advanced Inventory — Wave 2 (deepest)** — batch / lot / **serial** tracking,
  **expiry + FEFO** picking, landed cost, and **valuation methods** (FIFO /
  weighted-average) that upgrade Books' COGS beyond standard cost. One
  stock-dimension migration; see the deep-dive below.
- **Subscriptions / recurring billing** — retainers, memberships.
- **AI layer** — natural-language reports, receipt OCR, sales forecasting, anomaly
  detection, auto-categorization, an in-app assistant.

---

## Advanced Inventory (deep-dive)

A first-class stream in its own right — full plan in
`docs/advanced-inventory-plan.md`. The ledger stays the source of truth
(`stock_movements` append-only, `stock_levels` a derived cache); new dimensions
are added as nullable columns/tables, never a rewrite. It ships in two waves
across horizons:

| Wave | Feature | Horizon | Notes |
|---|---|---|---|
| W1 | **Low-stock alerts** | H1 | Rides the shared `notifications` table |
| W1 | **Barcode scanning** | H2 | Keyboard-wedge + camera; `GET /products/by-barcode` |
| W1 | **Stock-take / cycle-count** | H2 | Snapshot → count (scan-assisted) → post adjustments |
| W2 | **Bins / shelf sub-locations** | H2–H3 | Nullable `bin_id` on movements/levels |
| W2 | **Batch / lot / serial / expiry** | H3 | Tracking mode per product; FEFO picking |
| W2 | **Valuation methods** (FIFO / avg) | H3 | Feeds Books COGS (upgrades decision D1) |

The tracking dimension `(product, location, bin?, lot?)` + serial table is
designed **once** so the ledger migrates cleanly. Costing/valuation is the bridge
to Books — the `finalize`/`void` seam already anticipates it.

## Platform capabilities (cross-cutting, ongoing)

- **Multi-branch / multi-warehouse** (deepen beyond current locations).
- **Background jobs** — a queue + worker (already stubbed in infra) for email,
  FBR retries, PDF rendering, imports, scheduled reports.
- **Multi-currency** — when a customer needs it (single-currency PKR today).
- **Localization** — Urdu / RTL option.
- **Security & admin** — SSO, 2FA, richer audit trail (activities exist),
  data import/export, per-org backups (infra has nightly dumps).
- **Observability & performance** — metrics, tracing, error tracking.

## Compliance (Pakistan-first)

- **FBR Digital Invoicing** — shipped.
- **FBR sales-tax returns / annexures** — derive filings from the ledger.
- **Withholding tax** and **provincial revenue authorities** (SRB, PRA, …).
- **Data protection** and record-retention.

---

## Surfaces at a glance (the direct answer)

| Surface | Status | Horizon |
|---|---|---|
| Web app | ✅ shipped | — |
| Mobile app (iOS/Android) | planned | H2 |
| Desktop app (Win/Mac) | planned | H2 |
| POS | planned | H2 |
| WhatsApp | planned | H2 |
| Customer/Vendor portal | planned | H2 |
| Payment gateways | planned | H2 |
| Public API + webhooks | planned | H2 |

## Guiding principles

1. **Core first.** Every surface and product reuses one backend; no forks.
2. **Accounting-ready by construction.** Everything ties back to the ledger.
3. **Pakistan-first.** FBR, WhatsApp, and local payment rails are not afterthoughts.
4. **Offline where it counts.** POS and mobile must survive a dropped connection.
5. **One shared design system** across web, mobile, and desktop.
