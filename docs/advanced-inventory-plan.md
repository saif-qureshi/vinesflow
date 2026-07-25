# Advanced Inventory Plan

Extends the working inventory core (warehouses, ledger-backed stock, document
posting, adjust/transfer, committed/available, low-stock flag) with the features
a real warehouse needs. Two of them — **bins** and **batch/serial** — add a
dimension to how stock is tracked, so we design that dimension **once** and
migrate the ledger cleanly instead of twice.

## Principles

- **Ledger stays the source of truth.** `stock_movements` is append-only; every
  quantity change is a row. `stock_levels` is a derived cache. New dimensions are
  new *columns/tables*, never a rewrite of the ledger.
- **Extend the dimension once.** The target tracking key is
  `(product, location, bin?, lot?)` with serials in their own table. Bin and lot
  are **nullable** — orgs that don't use them keep working unchanged.
- **Costing is out of scope here.** `stock_movements.unit_cost` already exists;
  valuation (FIFO/average, inventory asset) belongs to Phase 7 (Books). This plan
  only *captures* cost where natural (opening stock, receipts) so Books can value
  it later.
- **Keep the core shared** (per `vineflow-multi-product`). Batch/serial/bin ride
  on the existing document posting seam, not a parallel system.

## Target stock model

Current: on-hand keyed by `(product_id, location_id)`.

Target:

```
stock_movements  += bin_id (nullable FK), lot_id (nullable FK)
stock_levels     += bin_id (nullable), lot_id (nullable)   # cache key extends
bins             (id, org_id, location_id, code, name, is_active)
stock_lots       (id, org_id, product_id, lot_no, expiry_date, mfg_date?, note)   # unique(org, product, lot_no)
serial_units     (id, org_id, product_id, serial_no, status, location_id, bin_id?, document_id?)  # unique(org, product, serial_no)
products         += tracking_mode  ('none' | 'lot' | 'serial')
```

- **Lot items**: on-hand is per `(product, location, bin?, lot)`. A lot carries
  its expiry. Outbound picking defaults to **FEFO** (earliest expiry first).
- **Serial items**: move in **whole units**; each unit is a `serial_units` row.
  On-hand = count of `in_stock` serials. No `lot_id` on serial movements.
- **`none`**: today's behaviour, unchanged.

One migration introduces the tables + nullable columns; existing rows get
`bin_id = lot_id = NULL`, `tracking_mode = 'none'` — fully backward compatible.

---

## Wave 1 — no core-model change (ship fast)

### 1. Opening-stock UI  (S)
Wire the existing `POST /inventory/opening` to the **item form**: an *Opening
Stock* section shown only when Track Inventory is on, with a qty per warehouse
and an optional **rate/unit** (stored as `movement.unit_cost`, ready for Books).
Editable only **before the first transaction** — once any non-opening movement
exists for the item, lock it and point to Adjust Stock.
- Backend: extend `OpeningStockInput` with `unit_cost`; add a "has movements"
  guard. Frontend: item-form section + per-warehouse rows.

### 2. Low-stock alerts  (S–M)
A `notifications` table (`org, type, title, body, entity_type, entity_id,
read_at`). After each movement post, if on-hand crosses **below `reorder_point`**,
create a `low_stock` notification (deduped while still low). Surface a bell +
notifications list in the app; email is a later add-on behind the same table.
- Reuses the existing `low_stock` flag/report for the list view.

### 3. Barcode scanning  (M)
A `ScanField` component: hardware keyboard-wedge scanners "just work" (type +
Enter); optional **camera** scan via a bundled JS decoder. Resolve a scan to a
product through a new `GET /products/by-barcode?code=`. Use it in the line-item
picker (invoices, receipts), Adjust Stock, and Stock-take. No model change
(`products.barcode` exists).

### 4. Stock-take / cycle-count  (M)
New `stock_counts` (`org, location, status: draft→counting→completed,
count_date, note`) + `stock_count_lines` (`product, bin?, system_qty` snapshot,
`counted_qty`, computed `variance`). Flow: create count (scope = location [+
category/low-stock filter]) → snapshot on-hand → enter counts (scan-assisted) →
review variances → **post**, which writes adjustment movements (reason "Cycle
count"). Builds on #3.

---

## Wave 2 — core-model extension (design once, migrate once)

### 5. Bins / shelf sub-locations  (M–L)
`bins` table under a location; add nullable `bin_id` to movements + levels.
Adjust/transfer/count/receive/pick gain an optional bin. Warehouses without bins
are unaffected. UI: manage bins under a warehouse; bin selector in stock ops.

### 6. Batch / lot / serial / expiry  (L, deepest)
- `products.tracking_mode`; `stock_lots`; `serial_units`; `movements.lot_id`.
- **Inbound** (goods receipt / opening): lot items capture `lot_no` + `expiry`
  per line (find-or-create the lot, tag the movement); serial items capture the
  serial numbers (one `serial_units` row each).
- **Outbound** (invoice / delivery challan): lot items pick lot(s) — **FEFO**
  default, manual override; movement decrements that lot. Serial items
  scan/select the exact serials → mark `sold`.
- **Expiry**: near-expiry report + alerts (reuse Wave-1 #2 machinery); FEFO
  guards against shipping expired stock.
- Depends on the bin decision (does a lot live in a bin?) — resolve with #5.

---

## Sequencing & risk

1. Opening-stock UI → 2. Low-stock alerts → 3. Barcode → 4. Stock-take
   *(each independent, no schema churn, immediately useful)*
5. Bins → 6. Batch/serial/expiry
   *(one stock-dimension migration; batch/serial is the highest-value but most
   invasive — build after bins so the dimension is settled)*

Each feature ships behind its own migration + tests, following the repo's
autogen-migration workflow. Costing/valuation is deliberately deferred to
Phase 7 (Books), which the `finalize`/`void` ledger seam already anticipates.
