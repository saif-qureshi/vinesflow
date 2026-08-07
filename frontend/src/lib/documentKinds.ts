import type { DocumentStatus, PartyRole, PaymentDirection } from "@/types";

export type DocumentKind =
  | "sales_order"
  | "delivery_challan"
  | "invoice"
  | "sales_receipt"
  | "credit_note"
  | "purchase_order"
  | "goods_receipt"
  | "bill";

export interface DocumentConversion {
  target: "delivery_challan" | "invoice" | "credit_note" | "goods_receipt" | "bill";
  label: string;
}

export interface DocumentKindConfig {
  kind: DocumentKind;
  apiPath: string;
  basePath: string;
  permission: string;
  partyRole: PartyRole;
  paymentDirection: PaymentDirection;
  /** Whether this document carries money owed (invoices/bills) vs. being purely
   *  operational (orders, challans). */
  tracksPayment: boolean;
  secondaryDateField?: "due_date" | "expected_shipment_date";
  priceField: "sale_price" | "purchase_price";
  labels: {
    singular: string;
    listTitle: string;
    listDescription: string;
    party: string;
    dateLabel: string;
    secondaryDateLabel?: string;
    referenceLabel: string;
    referencePlaceholder: string;
    warehouseHint: string;
    newAction: string;
  };
  statusOverrides?: Partial<Record<DocumentStatus, string>>;
  conversions?: DocumentConversion[];
  /** A counter sale is rung up for whoever is standing there: no party needed,
   *  a name and phone captured on the sale, and a till that takes the money. */
  counterSale?: boolean;
}

export const SALES_ORDER_CONFIG: DocumentKindConfig = {
  kind: "sales_order",
  apiPath: "sales-orders",
  basePath: "/sales/orders",
  permission: "sales_orders",
  partyRole: "customer",
  paymentDirection: "received",
  tracksPayment: false,
  priceField: "sale_price",
  labels: {
    singular: "Sales Order",
    listTitle: "Sales Orders",
    listDescription: "What customers have ordered but not yet been shipped",
    party: "Customer",
    dateLabel: "Order date",
    secondaryDateLabel: "Expected shipment date",
    referenceLabel: "Reference",
    referencePlaceholder: "Customer PO / reference",
    warehouseHint: "Stock will ship from here",
    newAction: "New Sales Order",
  },
  secondaryDateField: "expected_shipment_date",
  statusOverrides: { sent: "Confirmed" },
  conversions: [
    { target: "delivery_challan", label: "Create Delivery Challan" },
    { target: "invoice", label: "Convert to Invoice" },
  ],
};

export const DELIVERY_CHALLAN_CONFIG: DocumentKindConfig = {
  kind: "delivery_challan",
  apiPath: "delivery-challans",
  basePath: "/sales/challans",
  permission: "delivery_challans",
  partyRole: "customer",
  paymentDirection: "received",
  tracksPayment: false,
  priceField: "sale_price",
  labels: {
    singular: "Delivery Challan",
    listTitle: "Delivery Challans",
    listDescription: "Goods dispatched to customers",
    party: "Customer",
    dateLabel: "Dispatch date",
    referenceLabel: "Reference",
    referencePlaceholder: "Customer PO / reference",
    warehouseHint: "Stock ships from here",
    newAction: "New Delivery Challan",
  },
  statusOverrides: { sent: "Delivered" },
  conversions: [{ target: "invoice", label: "Convert to Invoice" }],
};

export const INVOICE_CONFIG: DocumentKindConfig = {
  kind: "invoice",
  apiPath: "invoices",
  basePath: "/sales/invoices",
  permission: "invoices",
  partyRole: "customer",
  paymentDirection: "received",
  tracksPayment: true,
  secondaryDateField: "due_date",
  priceField: "sale_price",
  labels: {
    singular: "Invoice",
    listTitle: "Invoices",
    listDescription: "Bill your customers and track what they owe",
    party: "Customer",
    dateLabel: "Invoice date",
    secondaryDateLabel: "Due date",
    referenceLabel: "Reference",
    referencePlaceholder: "Customer PO / reference",
    warehouseHint: "Stock ships from here",
    newAction: "New Invoice",
  },
  conversions: [{ target: "credit_note", label: "Create Credit Note" }],
};

export const SALES_RECEIPT_CONFIG: DocumentKindConfig = {
  kind: "sales_receipt",
  apiPath: "sales-receipts",
  basePath: "/sales/receipts",
  permission: "invoices",
  partyRole: "customer",
  paymentDirection: "received",
  tracksPayment: false,
  priceField: "sale_price",
  counterSale: true,
  labels: {
    singular: "Sales Receipt",
    listTitle: "Sales Receipts",
    listDescription: "Counter sales paid on the spot",
    party: "Customer",
    dateLabel: "Sale date",
    referenceLabel: "Reference",
    referencePlaceholder: "Slip / reference",
    warehouseHint: "Stock leaves from here",
    newAction: "New Sale",
  },
};

export const CREDIT_NOTE_CONFIG: DocumentKindConfig = {
  kind: "credit_note",
  apiPath: "credit-notes",
  basePath: "/sales/credit-notes",
  permission: "credit_notes",
  partyRole: "customer",
  paymentDirection: "received",
  tracksPayment: false,
  priceField: "sale_price",
  labels: {
    singular: "Credit Note",
    listTitle: "Credit Notes",
    listDescription: "Goods returned by customers and credits issued to them",
    party: "Customer",
    dateLabel: "Credit date",
    referenceLabel: "Reference",
    referencePlaceholder: "Reason / reference",
    warehouseHint: "Returned stock comes back here",
    newAction: "New Credit Note",
  },
  statusOverrides: { sent: "Issued" },
};

export const PURCHASE_ORDER_CONFIG: DocumentKindConfig = {
  kind: "purchase_order",
  apiPath: "purchase-orders",
  basePath: "/purchases/orders",
  permission: "purchase_orders",
  partyRole: "vendor",
  paymentDirection: "made",
  tracksPayment: false,
  priceField: "purchase_price",
  labels: {
    singular: "Purchase Order",
    listTitle: "Purchase Orders",
    listDescription: "What you have ordered from vendors but not yet received",
    party: "Vendor",
    dateLabel: "Order date",
    referenceLabel: "Reference",
    referencePlaceholder: "Vendor reference",
    warehouseHint: "Stock will be received into here",
    newAction: "New Purchase Order",
  },
  statusOverrides: { sent: "Issued" },
  conversions: [
    { target: "goods_receipt", label: "Receive Goods" },
    { target: "bill", label: "Convert to Bill" },
  ],
};

export const GOODS_RECEIPT_CONFIG: DocumentKindConfig = {
  kind: "goods_receipt",
  apiPath: "goods-receipts",
  basePath: "/purchases/receipts",
  permission: "goods_receipts",
  partyRole: "vendor",
  paymentDirection: "made",
  tracksPayment: false,
  priceField: "purchase_price",
  labels: {
    singular: "Goods Receipt",
    listTitle: "Goods Receipts",
    listDescription: "Goods received from vendors",
    party: "Vendor",
    dateLabel: "Receipt date",
    referenceLabel: "Reference",
    referencePlaceholder: "Delivery note no.",
    warehouseHint: "Stock is received into here",
    newAction: "New Goods Receipt",
  },
  statusOverrides: { sent: "Received" },
  conversions: [{ target: "bill", label: "Convert to Bill" }],
};

export const BILL_CONFIG: DocumentKindConfig = {
  kind: "bill",
  apiPath: "bills",
  basePath: "/purchases/bills",
  permission: "bills",
  partyRole: "vendor",
  paymentDirection: "made",
  tracksPayment: true,
  secondaryDateField: "due_date",
  priceField: "purchase_price",
  labels: {
    singular: "Bill",
    listTitle: "Bills",
    listDescription: "Record what you owe your vendors",
    party: "Vendor",
    dateLabel: "Bill date",
    secondaryDateLabel: "Due date",
    referenceLabel: "Vendor invoice #",
    referencePlaceholder: "Vendor's invoice number",
    warehouseHint: "Stock is received into here",
    newAction: "New Bill",
  },
  statusOverrides: { sent: "Open" },
};
