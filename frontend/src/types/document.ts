import type { SalespersonSummary } from "./salesperson";
import type { Address } from "./party";

export type DocumentStatus = "draft" | "sent" | "closed" | "void";

export type DocumentPaymentStatus = "unpaid" | "partial" | "paid" | "credited";

export type DiscountType = "amount" | "percent";

export interface DocumentParty {
  id: number;
  name: string;
  email: string | null;
}

export interface DocumentLine {
  id: number;
  product_id: number | null;
  tracking_mode: "none" | "lot" | "serial";
  bin_id: number | null;
  description: string;
  quantity: string;
  unit_price: string;
  discount_type: DiscountType;
  discount_value: string;
  discount: string;
  tax_rate_id: number | null;
  tax_amount: string;
  line_total: string;
  sort_order: number;
  lot_allocations: LotAllocation[];
  serials: DocumentLineSerial[];
}

export interface LotAllocation {
  id?: number;
  lot_id?: number | null;
  lot_number?: string | null;
  manufactured_date?: string | null;
  expiry_date?: string | null;
  quantity: number | string;
  lot?: {
    id: number;
    lot_number: string;
    manufactured_date: string | null;
    expiry_date: string | null;
  };
}

export interface DocumentLineSerial {
  id: number;
  serial_number: string;
  serial_unit_id: number | null;
}

export interface RelatedDocument {
  id: number;
  type: string;
  number: string;
  status: string;
}

export interface DocumentRecord {
  id: number;
  type: string;
  number: string;
  status: DocumentStatus;
  payment_status: DocumentPaymentStatus;
  party_id: number | null;
  party: DocumentParty | null;
  buyer_registered: boolean;
  credit_notes: RelatedDocument[];
  warehouse_id: number | null;
  issue_date: string;
  due_date: string | null;
  expected_shipment_date: string | null;
  reference: string | null;
  currency: string;
  notes: string | null;
  terms: string | null;
  billing_address: Address | null;
  shipping_address: Address | null;
  fbr_sale_origin: string | null;
  fbr_sale_destination: string | null;
  fbr_scenario_id: string | null;
  fbr_reason: string | null;
  fbr_reason_remarks: string | null;
  fbr_invoice_number: string | null;
  fbr_submitted_at: string | null;
  fbr_qr: string | null;
  subtotal: string;
  discount_total: string;
  tax_total: string;
  shipping: string;
  adjustment: string;
  total: string;
  amount_paid: string;
  amount_credited: string;
  salesperson: SalespersonSummary | null;
  commission_rate: string;
  commission_amount: string;
  balance_due: string;
  source_document_id: number | null;
  created_at: string;
  updated_at: string;
  lines: DocumentLine[];
}

export interface DocumentSummary {
  id: number;
  number: string;
  status: DocumentStatus;
  payment_status: DocumentPaymentStatus;
  issue_date: string;
  due_date: string | null;
  expected_shipment_date: string | null;
  currency: string;
  total: string;
  amount_paid: string;
  amount_credited: string;
  salesperson: SalespersonSummary | null;
  balance_due: string;
  party: DocumentParty | null;
}

export interface DocumentLineInput {
  product_id?: number | null;
  bin_id?: number | null;
  description: string;
  quantity: number;
  unit_price: number;
  discount_type?: DiscountType;
  discount_value?: number;
  tax_rate_id?: number | null;
  lot_allocations?: LotAllocation[];
  serial_numbers?: string[];
}

export interface DocumentInput {
  salesperson_id?: number | null;
  party_id: number;
  number?: string | null;
  issue_date?: string | null;
  due_date?: string | null;
  expected_shipment_date?: string | null;
  reference?: string | null;
  warehouse_id?: number | null;
  notes?: string | null;
  terms?: string | null;
  shipping?: number;
  adjustment?: number;
  fbr_sale_origin?: string | null;
  fbr_sale_destination?: string | null;
  fbr_scenario_id?: string | null;
  fbr_reason?: string | null;
  fbr_reason_remarks?: string | null;
  lines: DocumentLineInput[];
}

export interface TaxRate {
  id: number;
  name: string;
  rate: string;
  is_active: boolean;
  is_system: boolean;
}

export interface SellableItem {
  id: number;
  name: string;
  sku: string | null;
  description: string | null;
  image_url: string | null;
  uom_symbol: string | null;
  sale_price: string | null;
  purchase_price: string | null;
  fbr_rate: string | null;
  track_inventory: boolean;
  tracking_mode: "none" | "lot" | "serial";
  stock: string | null;
}
