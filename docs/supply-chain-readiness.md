# Supply Chain Readiness

Status: **product-positioning and roadmap analysis**  
Last reviewed: **1 August 2026**

## Executive summary

Vineflow already covers the transactional foundation of a supply chain for
trading, wholesale, retail, and distribution businesses:

- sales orders, delivery challans, invoices, receipts, and credit notes;
- purchase orders, goods receipts, bills, and supplier payments;
- products, variants, stock movements, adjustments, transfers, and multiple
  stock locations;
- customer and supplier balances;
- accounting records and FBR digital invoicing.

This makes Vineflow **supply-chain adjacent**, but not yet a complete Supply
Chain Management (SCM) platform. It records what was ordered, received, moved,
sold, and paid. A complete SCM product must also help a business **plan demand,
replenish stock, operate the warehouse, coordinate suppliers, fulfil orders,
manage transport, and measure supply-chain performance**.

The most accurate current positioning is:

> Business operations and ERP software for trading and distribution businesses,
> connecting purchasing, inventory, sales, accounting, and FBR compliance.

Vineflow should not be marketed as a complete supply-chain platform until the
minimum distribution-SCM capabilities identified below are shipped.

## Capability assessment

| Area | Available now | Already planned | Remaining gap |
|---|---|---|---|
| Purchasing | Purchase orders, goods receipts, bills, payments, and supplier balances | — | RFQs, purchase approvals, supplier contracts, lead times, and vendor performance scoring |
| Inventory | On-hand, committed and available stock; adjustments, transfers, and multiple locations | Low-stock alerts (H1); barcode scanning and cycle counts (H2); bins (H2–H3); batch, lot, serial, expiry, and FEFO (H3) | Replenishment rules, safety stock, stock-cover targets, and automatic purchase recommendations |
| Order fulfilment | Sales orders, delivery challans, invoices, and returns | POS and mobile/desktop operational surfaces (H2) | Stock allocation, pick lists, packing, partial fulfilment, backorders, and fulfilment status |
| Logistics | Delivery challan records goods leaving the business | Public API and webhooks (H2) may support integrations | Carriers, shipments, freight cost, routes, proof of delivery, and customer-facing delivery tracking |
| Suppliers | Supplier records, purchases, balances, and payments | Customer/vendor portal (H2) | Supplier onboarding, quotation comparison, confirmations, lead-time tracking, shared documents, and collaboration |
| Returns and quality | Credit notes, returns, and stock reversal | — | RMA workflow, receiving inspection, quarantine, reason analysis, disposition, and quality checks |
| Planning | Current quantities and a low-stock flag | Low-stock notifications (H1); sales forecasting in the later AI layer (H3) | Demand planning, reorder calculation, purchase suggestions, lead-time demand, and service-level planning |
| Supply-chain analytics | Sales, purchase, stock, aging, accounting, and dashboard reporting | Reporting expansion is part of H1 | Fill rate, stockout rate, inventory turns, days of supply, order cycle time, supplier lead time, on-time delivery, and forecast accuracy |
| External integration | Shared internal workflow | Public API/webhooks (H2); Shopify, WooCommerce, and Daraz connectors (H3) | Courier/carrier connectors, EDI, supplier-system integration, and marketplace fulfilment status sync |
| Manufacturing | Not part of the current product | BOM, assemblies, work orders, consumption, and COGS (H3) | Detailed production planning, MRP, capacity, scheduling, and shop-floor control if manufacturing becomes a target market |

## Capabilities already covered by the roadmap

The following should **not** be described as absent from Vineflow's direction.
They are already documented in `ROADMAP.md` and
`advanced-inventory-plan.md`:

### Horizon 1

- Low-stock alerts using the shared notification system.
- Expanded operational and financial reporting.

### Horizon 2

- Barcode scanning through hardware scanners and mobile cameras.
- Scan-assisted stock-take and cycle counting.
- Bin and shelf sub-locations beginning in H2 and deepening into H3.
- Mobile warehouse lookup and counting.
- Desktop/POS scanning and label-printing support.
- Customer/vendor portal.
- Public API and webhooks.

### Horizon 3

- Batch, lot, serial, and expiry tracking.
- FEFO picking for expiring inventory.
- Landed cost and FIFO/weighted-average valuation.
- E-commerce connectors for Shopify, WooCommerce, and Daraz.
- Manufacturing/BOM, assemblies, work orders, and consumption.
- Sales forecasting through the later AI layer.

## Minimum additions for distribution SCM

Vineflow does not need to build every enterprise SCM feature. To credibly
position the product as supply-chain software for wholesalers and distributors,
the minimum product set should be:

1. **Replenishment planning**
   - reorder points by product and location;
   - minimum, maximum, and safety-stock quantities;
   - supplier lead times;
   - suggested purchase orders based on available stock, open demand, incoming
     stock, and lead time.

2. **Warehouse execution**
   - deliver the already-planned barcode, stock-count, bin, batch, serial, and
     expiry capabilities;
   - add pick lists, packing confirmation, partial picks, and shipment readiness.

3. **Order allocation and backorders**
   - reserve available stock against confirmed sales orders;
   - expose shortages before a delivery is promised;
   - split partial fulfilments and retain the unfulfilled quantity as a
     backorder.

4. **Supplier operations**
   - RFQs and supplier quotation comparison;
   - purchase approval rules;
   - promised and actual delivery dates;
   - supplier lead-time and on-time-delivery reporting.

5. **Shipment and delivery management**
   - shipment records connected to delivery challans;
   - carrier, tracking number, freight cost, dispatch date, expected date, and
     delivered date;
   - courier API integrations and proof of delivery.

6. **Supply-chain reporting**
   - inventory turnover and days of supply;
   - fill rate and stockout rate;
   - order-to-dispatch time;
   - supplier lead time and on-time delivery;
   - backorder value and aging.

## Suggested sequencing

The existing roadmap should remain the foundation. The supply-chain additions
can fit around it without changing the shared-core strategy.

### Stage 1 — Inventory control

- Ship low-stock alerts.
- Add reorder rules and supplier lead times.
- Produce suggested purchase orders.
- Ship the planned barcode scanning and cycle counting.

### Stage 2 — Warehouse fulfilment

- Ship planned bins/shelf locations.
- Add allocation, pick lists, packing, partial fulfilment, and backorders.
- Connect shipment records to delivery challans.

### Stage 3 — Supplier and logistics coordination

- Add RFQs, approvals, quotation comparison, and supplier performance.
- Add courier integrations, tracking, freight cost, and proof of delivery.
- Introduce supply-chain KPIs.

### Stage 4 — Advanced inventory and optional manufacturing

- Ship the planned batch, lot, serial, expiry, FEFO, landed-cost, and valuation
  work.
- Add manufacturing depth only if factories become a deliberate target market.

## Product-positioning decision

Until the minimum distribution-SCM set is shipped, use:

> ERP for invoicing, inventory, purchasing, accounting, and FBR compliance.

After replenishment, warehouse fulfilment, supplier performance, shipments, and
supply-chain reporting are available, Vineflow can credibly use:

> Supply-chain and business operations software for trading and distribution
> businesses.

Manufacturing should remain optional. A distributor-focused SCM product does not
need MRP, production scheduling, or shop-floor control to be credible, but it does
need strong replenishment, warehouse, fulfilment, supplier, and logistics
capabilities.
