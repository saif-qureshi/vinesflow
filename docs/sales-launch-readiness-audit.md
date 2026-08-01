# Sales Module Launch Readiness Audit

Status: **launch-focused technical and product review**  
Last reviewed: **1 August 2026**

## Executive decision

Vineflow should not delay launch to reproduce Zoho Inventory's complete
`Sales Order -> Package -> Shipment` workflow.

The current product can launch with a smaller sales workflow, provided that the
data-integrity, inventory, payment, and accounting risks in this document are
fixed first.

Recommended launch workflow:

```text
Sales Order -> Invoice -> Payment
     |
     +-> Delivery Challan -> Invoice
```

The Delivery Challan is an optional document for goods being transported. It
must not be presented as a Package or Shipment substitute. Packages, shipments,
carrier tracking, proof of delivery, and multi-stage fulfilment can be added
after launch.

## Scope

This review covers:

- sales orders, delivery challans, invoices, credit notes, and payments;
- document conversion and status transitions;
- inventory and accounting effects;
- FBR submission;
- permissions, customer selection, printing, and reporting;
- the minimum changes required for a safe initial release.

This is not a proposal to copy Zoho. Zoho is used only to clarify the difference
between a normal fulfilment workflow and a Delivery Challan workflow.

## Product model for launch

### Normal sale

```text
Sales Order: Draft -> Confirmed -> Invoiced/Closed
Invoice:     Draft -> Finalized -> Partially Paid/Paid
Payment:     Draft -> Submitted
```

An invoice may also be created directly when a Sales Order is unnecessary.

### Sale involving a Delivery Challan

```text
Delivery Challan: Draft -> Open/Dispatched -> Delivered/Returned
                                      |
                                      +-> Invoice for accepted goods
```

For launch, a Delivery Challan should be used when goods are physically moved
before the final invoice is issued. Examples include goods sent on approval,
job work, uncertain accepted quantities, or another movement that may not result
in a complete sale.

The system does not currently have enough status depth to represent this model
accurately. Until that is corrected, the UI must not label every finalized
Delivery Challan as `Delivered` automatically.

### Explicitly deferred fulfilment model

The following is useful but is not required for the initial launch:

```text
Sales Order -> Package 1..N -> Shipment 1..N -> Delivered
```

It should be introduced later when Vineflow supports partial quantities,
backorders, packing operations, and separate shipment events.

## Launch assessment

The basic happy path works, and the targeted backend test suites pass. However,
the module is not launch-safe yet because several permitted operations can
produce incorrect stock, accounts receivable, revenue, or customer balances.

The most serious problem is not the absence of Packages or Shipments. It is that
the current conversion, void, payment, and credit-note rules do not preserve
transactional integrity.

## P0 — Must fix before launch

### 1. Restrict payment allocations to valid accounting documents

Current behavior:

- a received payment can be allocated to any broad sales document type,
  including a Sales Order, Delivery Challan, or Credit Note;
- submission does not fully revalidate the target document's organization,
  party, status, and type;
- changing a draft payment's party can retain allocations belonging to the old
  party.

Impact:

- accounts receivable can be credited even though no invoice posted an
  accounts-receivable debit;
- a payment can be submitted after its target document is voided or changed;
- customer balances can be assigned to the wrong customer.

Required launch rule:

- customer receipts may allocate only to finalized sales invoices;
- supplier payments may allocate only to finalized purchase bills;
- organization, party, currency, document status, and outstanding amount must be
  revalidated during submission;
- changing the payment party must clear or revalidate every allocation.

Primary implementation area:

- `backend/app/modules/payments/service.py`

### 2. Prevent voiding documents that have active downstream documents

Current behavior:

- the void operation checks payments but does not consistently block active
  converted documents;
- a Delivery Challan can be invoiced and then voided, reversing stock while the
  invoice remains active;
- an invoice can be voided while a draft Credit Note still references it, and
  the Credit Note can later be finalized.

Impact:

- stock, cost of goods sold, revenue, tax, and accounts receivable can disagree;
- the audit trail no longer represents a valid business sequence.

Required launch rule:

- a document cannot be voided while it has a non-void downstream document;
- the user must void dependent documents in reverse order;
- finalizing a dependent document must revalidate that its source is still
  active and eligible.

Primary implementation area:

- `backend/app/modules/documents/service.py`

### 3. Stop closing a source document when only a draft target is created

Current behavior:

- converting a document creates a draft target but immediately marks the source
  as closed;
- there is no line-level record of how much was ordered, delivered, invoiced, or
  returned;
- more than one target can be created from the same source;
- converted target lines remain editable, while stock suppression is decided at
  the whole-document level.

Impact:

- a Sales Order appears complete before an Invoice or Delivery Challan is
  finalized;
- duplicate or conflicting invoices can be created;
- editing converted lines can cause stock movements to be skipped incorrectly.

Required launch rule:

For the initial release, choose the simpler safe constraint:

- allow only one active conversion of each supported target type;
- keep the source open while the target is draft;
- close the source only when the target is finalized;
- prevent changing product identity and quantities on a converted target, or
  perform complete source-quantity validation;
- do not claim partial fulfilment support at launch.

This deliberately avoids building the complete allocation model before launch.

Primary implementation areas:

- `backend/app/modules/documents/service.py`
- `backend/app/modules/documents/models.py`

### 4. Enforce inventory availability and posting idempotency

Current behavior:

- document finalization can reduce stock without checking available quantity;
- stock levels do not have a database uniqueness constraint for the combination
  of organization, product, and location;
- document stock movements do not have a strong idempotency guarantee;
- document finalization does not lock the stock row against concurrent changes;
- a warehouse ID is accepted without complete organization and active-status
  validation.

Impact:

- negative stock can be created unintentionally;
- concurrent finalization can oversell stock;
- duplicate stock-level rows or duplicate movements can corrupt balances;
- a location from another organization can be referenced.

Required launch rule:

- validate that every warehouse belongs to the current organization and is
  active;
- use the organization's active default location when none is supplied;
- make the negative-stock policy explicit and default it to blocked;
- add a unique organization/product/location constraint;
- make stock posting atomic and idempotent;
- lock or conditionally update stock during outbound posting.

Primary implementation areas:

- `backend/app/modules/documents/service.py`
- `backend/app/modules/inventory/service.py`
- `backend/app/modules/inventory/models.py`

### 5. Correct Credit Note accounting and stock valuation

Current behavior:

- crediting more than an invoice's outstanding amount is rejected, so a fully
  paid invoice cannot be credited correctly;
- applying a Credit Note mutates the invoice's paid amount/status rather than
  representing a customer credit or refund;
- Credit Note lines can contain products and quantities unrelated to the source
  invoice;
- returned stock can be valued using the selling price instead of its inventory
  cost.

Impact:

- legitimate post-payment returns cannot be processed;
- customer credit and cash refund obligations are not represented;
- inventory value and cost of goods sold can be overstated;
- unrelated goods can be returned against an invoice.

Required launch rule:

- constrain Credit Note lines and quantities to the source invoice;
- reverse inventory at the original cost basis, not the selling price;
- allow a Credit Note against a paid invoice;
- represent the result as an unapplied customer credit or refund, rather than
  rewriting invoice payment history.

If customer credits and refunds cannot be implemented before release, Credit
Notes should be clearly marked limited and restricted to unpaid invoice amounts.

Primary implementation area:

- `backend/app/modules/documents/service.py`

### 6. Make FBR submission recoverable

Current behavior:

- the external FBR submission occurs before local stock, accounting, and
  database finalization complete;
- shipping and adjustment amounts included in the local total are not fully
  represented in the FBR item payload.

Impact:

- FBR can accept an invoice that the local system later fails to finalize;
- the FBR total can differ from the local invoice total;
- retrying after an ambiguous failure can create duplicate external actions.

Required launch rule:

- validate the complete local posting before external submission;
- make the FBR request idempotent and persist submission state;
- support a recoverable `submission pending/failed` state;
- reconcile shipping, adjustments, discounts, and taxes between local and FBR
  totals.

Primary implementation areas:

- `backend/app/modules/fbr/invoice.py`
- `backend/app/modules/fbr/service.py`
- `backend/app/modules/documents/service.py`

### 7. Protect historical records

Current behavior:

- deleting a product can cascade into stock history;
- deleting a party can remove the relationship used by historical reports;
- prints and FBR payloads use a mixture of saved document fields and current
  party/product data.

Impact:

- historical inventory evidence can disappear;
- old invoices can change when customer or product master data changes;
- customer reports can omit transactions whose party was deleted.

Required launch rule:

- products and parties referenced by transactions must be archived, not
  physically deleted;
- finalized documents must preserve customer name, addresses, tax identifiers,
  product description, SKU, unit, tax treatment, and other legal fields as
  snapshots;
- finalized document rendering and submission must use those snapshots.

Primary implementation areas:

- `backend/app/modules/products/service.py`
- `backend/app/modules/parties/service.py`
- `backend/app/modules/documents/models.py`
- `backend/app/modules/documents/print/mapper.py`

## P1 — Fix for launch quality if time allows

### Dates and Delivery Challan wording

The Delivery Challan form now presents `Expected Shipment Date`, but the stored
field is still the generic `due_date`, which may be populated from customer
payment terms. Printed output can still call it `Due date`.

Before launch, either:

- add a real `expected_shipment_date` field; or
- consistently treat `due_date` as the expected shipment date only for Delivery
  Challans, including defaulting, API names, filters, and printing.

A finalized Delivery Challan should become `Open` or `Dispatched`. `Delivered`
must be a separate user action because finalizing a document does not prove that
the customer received the goods.

### Currency consistency

The backend document model defaults to PKR while parts of the frontend format
values using organization currency. Document creation does not consistently
snapshot organization or customer currency.

Before launch, enforce a single organization currency if multi-currency is not
supported. Store that currency on every document and use it consistently in the
UI, PDF, accounting entries, payments, and reports.

### Permissions

Conversion currently checks permission on the source module but not always the
permission required to create the target document. Navigation and quick-create
actions also expose unavailable or unauthorized modules.

Required behavior:

- conversion requires read/update permission on the source and create permission
  on the target;
- buttons and navigation follow the same permission rules as the API;
- the default Member role must be able to complete any payment workflow exposed
  by the UI, or the action must be hidden.

### Party and product validation

Document APIs should enforce customer/vendor roles and active status. They must
also reject inactive products and inactive tax definitions. The customer picker
currently risks showing only the first page of results, so server-side search or
complete pagination is required for organizations with more than 25 parties.

### Reporting consistency

Current sales reports use different definitions of sales: some include tax and
charges, some use line totals, and Credit Notes are not consistently subtracted.

For launch, publish and test one definition for each metric:

- net sales excluding tax;
- tax collected;
- shipping and adjustments;
- returns and Credit Notes;
- gross invoice value;
- cash collected;
- outstanding receivables.

## Deferred until after launch

The following should not block the initial release:

- Package and Shipment modules;
- partial packing, partial shipping, and backorders;
- multiple fulfilments against one Sales Order;
- carrier and courier integrations;
- tracking numbers and customer tracking pages;
- proof of delivery;
- pick lists, packing slips, and warehouse scanning;
- batch, serial, expiry, and FEFO fulfilment;
- multi-currency, if the product is explicitly launched as PKR-only;
- advanced customer-credit application across invoices.

Deferred features must not be implied in the UI or marketing. In particular,
Vineflow should not claim partial fulfilment or shipment tracking until it can
record those states independently.

## Required launch tests

The existing targeted tests validate the basic happy path, but several of them
also encode unsafe current behavior such as closing a source immediately after
conversion.

Add end-to-end service tests for:

1. payment allocation rejects Sales Orders, Delivery Challans, Credit Notes,
   void invoices, another customer's invoices, and another organization's
   invoices;
2. changing a payment party cannot retain incompatible allocations;
3. a document with an active downstream document cannot be voided;
4. a draft conversion does not close its source;
5. duplicate conversion is blocked under the launch constraint;
6. converted line products and quantities cannot exceed or diverge from the
   source;
7. insufficient stock blocks finalization without partial stock/accounting
   effects;
8. concurrent finalization cannot oversell or double-post;
9. cross-organization and inactive warehouse IDs are rejected;
10. a paid invoice can follow the chosen Credit Note/refund policy;
11. returned stock uses the original inventory cost;
12. FBR totals equal local totals when shipping, discounts, tax, and adjustments
    are present;
13. an FBR success followed by a local failure enters a recoverable state;
14. archived parties and products remain visible on historical documents and
    reports;
15. organization currency is identical across document, payment, PDF,
    accounting, and reporting outputs.

## Launch gate

The sales module is ready for release when all of the following are true:

- [ ] invalid payment allocations are impossible;
- [ ] downstream dependency checks protect void and finalization operations;
- [ ] conversion cannot close, duplicate, or alter a source incorrectly;
- [ ] stock posting is organization-safe, atomic, and idempotent;
- [ ] the Credit Note limitation or full customer-credit policy is explicit and
      enforced;
- [ ] FBR/local posting failures are recoverable and totals reconcile;
- [ ] referenced products and parties are archived rather than deleted;
- [ ] Delivery Challan dates, labels, statuses, and PDF output agree;
- [ ] permissions shown in the UI match backend enforcement;
- [ ] sales reports use documented, tested definitions;
- [ ] all P0 regression tests pass.

## Post-launch direction

After the simple launch workflow is stable and customers demonstrate a need for
warehouse fulfilment, introduce Packages and Shipments as separate operational
entities. At that point, add per-line quantities for ordered, packed, shipped,
invoiced, and returned goods.

The eventual model can be:

```text
Sales Order
  +-> Package(s) -> Shipment(s) -> Delivered
  +-> Invoice(s) -> Payment(s)

Delivery Challan -> Delivered/Returned -> Optional Invoice
```

That future model should be driven by customer usage, not treated as a launch
prerequisite.

## Reference clarification

Zoho's products demonstrate why the two workflows must remain conceptually
separate:

- Zoho Inventory's normal fulfilment uses Sales Orders, Packages, and Shipments.
- Zoho Books and Zoho Invoice provide Delivery Challans.
- Zoho Inventory also exposes Delivery Challans in supported editions, but as a
  separate goods-movement document rather than the replacement for Package and
  Shipment.

Official references:

- [Zoho Inventory: Packages](https://www.zoho.com/us/inventory/help/sales-orders/packages.html)
- [Zoho Inventory: Delivery Challans](https://www.zoho.com/in/inventory/help/delivery-challan/delivery-challan.html)
- [Zoho Books: Delivery Challans](https://www.zoho.com/in/books/help/delivery-challan/)
- [Zoho Invoice](https://www.zoho.com/in/invoice/)
