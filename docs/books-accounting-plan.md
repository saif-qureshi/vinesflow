# Vineflow Books — Accounting (GL) Phase Plan

Status: **design**. This is the build plan for **Books**, Vineflow's double-entry
general ledger. It supersedes Part B of `docs/payments-and-accounting-plan.md`
(kept for the payment-capture history) and is the authoritative sequencing doc.

**References**
- `~/projects/accountings` — a mature double-entry engine (NestJS/MikroORM). We
  port its *architecture*: one posting service, immutable ledger, control
  accounts, period locks, reverse-don't-delete. We also **avoid its known bugs**
  (logged there as C17–C30): mid-year balance-sheet imbalance, voucher-numbering
  race, money truncation, header-only posting.
- **Zoho Books** — the feature bar and vocabulary SMB users expect: Chart of
  Accounts, Manual Journals, Banking + reconciliation, Opening Balances, and the
  report set (P&L, Balance Sheet, Cash Flow, Trial Balance, General Ledger,
  Account Transactions, AR/AP aging).

**The core bet (already paid off).** Vineflow's commerce layer was built
accounting-ready. The `LedgerPoster` seam is already wired:
`DocumentService.finalize/void` call `post_document`/`reverse_document`;
`PaymentService.submit/cancel` call `post_payment`/`reverse_payment`. Today they
hit `NullLedgerPoster`. Books = build the GL, implement `RealLedgerPoster`, swap
the binding. **The operational services never change**, and history can be
**backfilled** from the immutable document/payment/stock trail.

---

## 0. Principles (inherited from both references)

1. **One posting service.** Every ledger write — automatic or manual — goes
   through `PostingService.post_voucher`. No module writes `ledger_entries` directly.
2. **Immutable ledger.** A posted entry is never updated or deleted. Corrections
   are *reversals* (mirror voucher) or new documents.
3. **Balanced or nothing.** ΣDebit == ΣCredit enforced with **Decimal**
   (quantized), never float. Ledger money at `Numeric(18,4)` so per-unit cost
   lines don't drift; document/payment amounts stay `Numeric(18,2)`.
4. **Control accounts** (AR, AP, Inventory, tax, revenue, COGS, retained
   earnings) move **only** through the documents that own their subledger. A
   hand-written journal cannot touch them (`allow_control_accounts` opt-in for
   system paths only).
5. **Subledger on the line.** AR/AP lines carry `party_id` so the customer/vendor
   subledger reconciles to the control-account balance.
6. **Post into open periods only.** A posting date resolves to a period in an
   *active* fiscal year whose period is *open*; else it's rejected.
7. **Configurable, not hard-coded.** Every role→account link lives in the
   `accounting` settings group, seeded per org and editable.
8. **Backfillable by construction.** Each voucher is addressable by
   `(source_type, source_id)`; posting is idempotent so a replay can't double-post.

---

## Phase B0 — Ledger engine (foundation)

**Goal:** a correct, tested double-entry core with nothing wired to it yet.

**Schema** (one autogen Alembic migration; models first, then
`alembic revision --autogenerate`):

| Table | Key columns |
|---|---|
| `accounts` | `org_id, parent_id, code, name, account_type (asset·liability·equity·income·expense), normal_balance (debit·credit), is_control_account, is_postable, is_active`. Unique `(org_id, code)`. |
| `fiscal_years` | `org_id, name, starts_on, ends_on, status (active·closed)` |
| `accounting_periods` | `org_id, fiscal_year_id, name, period_no, starts_on, ends_on, status (open·locked·closed)`. Unique `(org, fy, period_no)`. |
| `accounting_vouchers` | `org_id, fiscal_year_id, period_id, voucher_type, number, document_date, posting_date, description, total_debit, total_credit, status (draft·posted·reversed·cancelled), posted_at/by, reversed_from_id, source_type, source_id`. Unique `(org, voucher_type, number)`; index `(org, source_type, source_id)`. |
| `voucher_lines` | `voucher_id, account_id, party_id, line_no, debit, credit, description` |
| `ledger_entries` | denormalized posted GL — `org_id, account_id, party_id, voucher_id, voucher_line_id, fiscal_year_id, period_id, voucher_type, number, posting_date, line_no, debit, credit, status`. Indexes: `(org, posting_date)`, `(org, account, posting_date)`, `(org, party, posting_date)`, `(org, source…)`. |

**`PostingService`** (port of `accountings/posting.service.ts`):
- `resolve_open_period(org_id, posting_date)` → period or `BadRequestError`.
- `validate_lines(lines, allow_control_accounts=False)` → ≥2 lines; each line
  debit **xor** credit; accounts active+postable; control-account guard; parties
  valid; ΣDr == ΣCr (Decimal). Returns totals.
- `post_voucher(voucher, lines, *, allow_control_accounts)` → draft-only; resolve
  period; validate; write one immutable `ledger_entry` per line; stamp
  `posted_at/by`, status=`posted`.
- `reverse_voucher(voucher, posting_date)` → mirror lines (swap Dr/Cr), post as
  `reversal`, mark original `reversed`, set `reversed_from_id`.

**Voucher numbering** — reuse the existing `document_sequences`/numbering pattern
with a **row-locked per-`(org, voucher_type)` sequence** (fixes the reference's
numbering race). Prefixes: `JV, OPN, RV, ADJ, PCV` + document-driven `SV`
(invoice), `RCP` (receipt), `CN` (credit note), `PV` (bill), `PPV` (payment made),
`DNV` (vendor credit), `GRV` (goods receipt), `EXV` (expense), `SAV` (stock adj).

**Tests:** balanced voucher posts; unbalanced fails; <2 lines fails; closed
period rejects; posted entry immutable; reversal references original & nets to
zero; control-account guard blocks a manual line but allows a system line.

**Exit:** engine is reliable and unit-tested; no document touches it yet.

---

## Phase B1 — Chart of Accounts + fiscal setup (per-org bootstrap)

**Goal:** every new org boots with a usable chart, mappings, and an open year.

- **Seed default chart** (`accounting_service.seed_chart(org_id)`), added to
  `OrgService.create_org_with_owner` alongside the existing seeders. Chart
  (from the reference, PKR-localized): Cash 1110 · Bank 1120 · **AR 1130** ·
  **Inventory 1140** · **Input Tax 1150** · **AP 2110** · **Output/Sales Tax
  Payable 2120** · **GRNI 2130** · Owner Equity 3100 · **Retained Earnings 3200**
  · Opening Balance Equity 3300 · **Sales Revenue 4100** · Sales Returns 4200 ·
  **COGS 5100** · Operating Expenses 5200 · Inventory Adjustments 5300. (**bold** =
  control account.)
- **Seed account-mapping** into the `accounting` settings group: `ar_account`,
  `ap_account`, `cash_account`, `bank_account`, `sales_revenue`,
  `sales_tax_payable`, `input_tax`, `inventory`, `cogs`, `grni`,
  `retained_earnings`, `opening_balance_equity`, `inventory_adjustment`.
- **Auto-create fiscal year + 12 monthly periods** at org creation, derived from
  `organizations.fiscal_year_start_month` (default 7 → Jul–Jun). Idempotent.
- **API + RBAC** — new `accounting` (+ `journals`) RBAC module. Accounts CRUD,
  fiscal-year CRUD + `close`, period `lock/unlock`. Guard: can't delete an
  account with ledger entries; can't edit FY dates after periods exist.
- **Frontend:** Chart-of-Accounts tree + account form; Fiscal Years / Periods
  screens with lock toggles (Zoho-style "Accountant" area).

**Exit:** a fresh org has a chart, mappings, and an open current year; accounts
and periods are manageable from the UI.

---

## Phase B2 — Automatic posting: Sales side + `RealLedgerPoster`

**Goal:** flip the seam on; sales documents post real double-entry.

- Implement **`RealLedgerPoster`** (merges the reference's per-service line
  builders + `AccountingPostingService`). It reads the account mapping, builds
  Dr/Cr lines, and calls `post_voucher(..., allow_control_accounts=True)` on the
  **caller's transaction** (atomic with the document). Bind it in place of
  `NullLedgerPoster` (module-level `ledger_poster`).
- **Idempotency + reversal:** a document already carrying a posted voucher
  (`source_type,source_id`) is skipped; `reverse_document`/`reverse_payment` post
  the mirror.

**Posting map — sales:**

| Event (on finalize/submit) | Debit | Credit |
|---|---|---|
| **Invoice** | AR *(party)* — total | Sales Revenue — subtotal; Sales Tax Payable — tax |
| …stock-relieving invoice *(same voucher)* | COGS — cost | Inventory — cost |
| **Payment Received** | Cash *or* Bank *(by `method`)* — amount | AR *(party)* — amount |
| **Credit Note** | Sales Returns — subtotal; Sales Tax Payable — tax | AR *(party)* — total |
| …with restock | Inventory — cost | COGS — cost |

- **COGS cost source** = the `unit_cost` already stamped on the outbound
  `stock_movement` (see decision D1). COGS folds into the invoice voucher so it
  self-balances; if a Delivery Challan already relieved the stock, the invoice
  **skips COGS** (no double count) and the challan carries it.

**Tests (integration):** finalize invoice → balanced `SV` voucher + AR/Rev/Tax
ledger rows; receipt → `RCP` Dr Bank/Cr AR; void invoice → reversal nets to zero;
**Trial Balance balances** after a mixed run.

**Exit:** all sales activity posts to the GL and reverses cleanly; TB balances.

---

## Phase B3 — Automatic posting: Purchase, Expense + Inventory side

**Goal:** complete the double-entry coverage across every commerce document,
including direct expenses.

**New capture module — Expenses.** Vineflow has **no expense entity yet**; Books
introduces a lightweight one (mirrors Zoho "Expenses" and the reference's
`expenses` service). An **Expense** is a *direct spend paid immediately* —
distinct from a Bill (a Bill is payable → AP; an Expense hits Cash/Bank now):
- Fields: `org_id, number (EXV), document_date, posting_date, expense_account_id
  (a category under 5000), party_id (optional vendor), method (cash·bank·cheque·
  card), amount, tax_amount, grand_total, reference, status (draft·submitted·
  cancelled)` + AuditMixin.
- Lifecycle mirrors payments: draft → **submit** (posts) → **cancel** (reverses),
  reusing the same `LedgerPoster` seam.
- CRUD + submit/cancel API under a new RBAC `expenses` module; a create/list/view
  UI in the Purchases area. Users add expense **categories** as postable accounts
  under `5000 Expenses` (Rent, Utilities, Salaries, …) via the B1 chart UI.
- **This is the source of the dashboard "Expenses"/net-profit figure** that was
  deferred earlier ("expenses will later come from accounting") — the dashboard
  reads expense-account activity from the ledger once B3 + B6 land.

**Posting map — purchases, expenses & inventory:**

| Event | Debit | Credit |
|---|---|---|
| **Bill** finalized | Inventory *or* Expense — subtotal; Input Tax — tax | AP *(party)* — total |
| **Goods Receipt** (before bill) | Inventory — cost | GRNI — cost |
| **Bill** matching a GR | GRNI — cost; Input Tax — tax | AP *(party)* — total |
| **Payment Made** | AP *(party)* — amount | Cash/Bank *(by method)* — amount |
| **Vendor Credit / Debit Note** | AP *(party)* — total | Inventory/Expense; Input Tax |
| **Expense** submitted | Expense category — amount; Input Tax — tax | Cash/Bank *(by method)* — grand total |
| **Stock Adjustment** (+) | Inventory — value | Inventory Adjustments — value |
| **Stock Adjustment** (−) | Inventory Adjustments — value | Inventory — value |

- GRNI models "received but not yet invoiced" so inventory is valued at receipt
  and the bill clears GRNI rather than re-hitting inventory (Zoho + reference
  both do this).

**Tests:** bill → `PV` Dr Inventory+InputTax / Cr AP; payment made → `PPV`;
expense → `EXV` Dr Expense+InputTax / Cr Cash-or-Bank, reverses on cancel;
stock adjustment posts to Inventory + Inventory Adjustments; full
sales+purchase+expense run keeps TB balanced and AR/AP subledgers reconcile to
their controls.

**Exit:** 100% of finalized documents, submitted payments, and expenses post
correct, reversible double-entry.

---

## Phase B4 — Manual journals + opening balances

**Goal:** the accountant's manual tools (Zoho "Manual Journals" + "Opening Balances").

- **Manual Journal Voucher** (`JV`): create/edit/post/reverse UI; multi-line
  Dr/Cr grid; balance indicator; **control accounts rejected** (guides the user
  to the owning document instead). Draft → posted lifecycle.
- **Opening Balances** (`OPN`): a guided flow to enter a migrating business's
  starting trial balance — customer/vendor opening balances (post to AR/AP with
  the party, offset to Opening Balance Equity), bank/cash, inventory. Balanced
  against Opening Balance Equity.
- **Adjustment / Contra** vouchers (bank↔cash transfers).

**Exit:** an accountant can record any entry the automatic postings don't cover,
and migrate an existing business's opening position.

---

## Phase B5 — Backfill (retro-ledger)

**Goal:** build historical GL for orgs that traded before Books existed.

- CLI/admin command `books backfill --org <id>`: in posting-date order, replay
  `post_document` over every finalized (`sent`/`void`) document and `post_payment`
  over every `submitted`/`cancelled` payment.
- **Idempotent** via `(source_type, source_id)` — reruns skip already-posted
  sources. Reports progress and anything unpostable (e.g. missing cost).
- Validates: post-backfill **Trial Balance balances** and AR/AP controls equal
  the sum of open document balances.

**Exit:** any existing org can be brought onto Books with a complete, correct
historical ledger and zero manual re-entry.

---

## Phase B6 — Reports

**Goal:** the Zoho Books financial report set, sourced from `ledger_entries`.

| Report | Source | Notes |
|---|---|---|
| **Trial Balance** | ledger net per account | as-of date |
| **General Ledger** | ledger entries, filterable | by account/date/party |
| **Account Transactions / Statement** | ledger for one account | running balance |
| **Profit & Loss** | income − expense accounts | period range |
| **Balance Sheet** | asset/liability/equity **+ dynamic current-year earnings** | *fixes reference C17 — nets income/expense into equity so it balances mid-year without a close* |
| **Cash Flow Statement** | cash/bank account movement | Zoho parity |
| **AR Aging / AP Aging** | open documents by `balance_due` + `payment_status` | already derivable; reconciles to AR/AP controls |

**Frontend:** report screens under the existing `reports` area; date-range and
account filters; export.

**Exit:** users can see TB, P&L, Balance Sheet, Cash Flow, GL, and aging; all tie
back to the ledger.

---

## Phase B7 — Period close, year-end & polish

**Goal:** close the accounting loop.

- **Period lock** enforcement end-to-end (posting rejected into locked periods;
  UI to lock/unlock with permission).
- **Fiscal-year close** (`PCV`): a `period_closing` voucher moves net
  income/expense to Retained Earnings and locks the year's periods; new year +
  periods auto-created.
- **Banking / reconciliation** *(Zoho feature — optional, evaluate after B6)*:
  mark ledger cash/bank lines reconciled against a statement.
- Audit surface: link each voucher to its `source` document; show "Journal" tab
  on invoices/bills/payments (Zoho-style).

**Exit:** periods lock, years close to retained earnings, and every posting is
traceable to its source.

---

## Key decisions (recommendations — confirm before B0/B2)

- **D1 — COGS costing.** Post COGS at the `unit_cost` already recorded on each
  outbound stock movement (standard cost = `product.purchase_price`).
  *Recommended:* uses existing data, backfillable, gives gross margin from day
  one. Upgrade to weighted-average/FIFO later behind the same posting map.
  *(Alt: defer COGS — post only AR/Revenue/Tax/Cash until costing lands.)*
- **D2 — Ledger money precision.** `Numeric(18,4)` for `ledger_entries`,
  `voucher_lines`, and voucher totals (cost lines need >2dp); documents/payments
  stay `Numeric(18,2)`. Avoids the reference's truncation bug.
- **D3 — Periods.** Auto-create monthly periods with open/lock from day one
  (matches both references; needed for close + locked-period safety).
- **D4 — Numbering.** Row-locked per-`(org, voucher_type)` sequence to avoid the
  concurrent-post collision the reference logged.
- **D5 — Single currency.** PKR only — skip Zoho's multi-currency/base-currency
  machinery for now (org is single-currency).

## Explicitly out of scope (v1)

Multi-currency · budgets · recurring journals · full bank feeds/auto-import ·
tax filing reports (FBR already owns e-invoicing/tax) · consolidated multi-org
books.

## Dependencies & sequencing

B0 → B1 → **B2 (go-live seam flip)** → B3 → {B4, B5 independent} → B6 → B7.
B2 is the milestone that makes Books "live" for new activity; B5 makes it
complete for existing activity; B6 makes it *useful* to the business.
