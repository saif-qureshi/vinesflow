import type { Address } from "./party";

export interface Warehouse {
  id: number;
  name: string;
  code: string | null;
  address: Address | null;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
}

export interface WarehouseInput {
  name: string;
  code?: string | null;
  address?: Address | null;
  is_default?: boolean;
  is_active?: boolean;
}

export interface Bin {
  id: number;
  location_id: number;
  code: string;
  name: string;
  is_active: boolean;
  created_at: string;
}

export interface BinInput {
  location_id: number;
  code: string;
  name: string;
  is_active?: boolean;
}

export interface InventoryItem {
  id: number;
  name: string;
  sku: string | null;
  is_variant: boolean;
  tracking_mode: "none" | "lot" | "serial";
  uom_symbol: string | null;
  reorder_point: number | null;
  on_hand: string;
  is_low: boolean;
}

export interface StockMovement {
  id: number;
  product_id: number;
  location_id: number;
  bin_id: number | null;
  lot_id: number | null;
  qty_delta: string;
  type: string;
  reason: string | null;
  note: string | null;
  created_at: string;
}

export interface ItemStock {
  on_hand: string;
  opening_stock: string;
  committed: string;
  available: string;
  to_be_shipped: string;
  to_be_received: string;
  to_be_invoiced: string;
  to_be_billed: string;
  by_location: { location_id: number; quantity: string }[];
  by_bin: { location_id: number; bin_id: number | null; quantity: string }[];
  by_lot: { location_id: number; bin_id: number | null; lot_id: number; quantity: string }[];
}

export interface StockLot {
  id: number;
  product_id: number;
  lot_number: string;
  manufactured_date: string | null;
  expiry_date: string | null;
  note: string | null;
  is_active: boolean;
  quantity: string;
}

export interface SerialUnit {
  id: number;
  product_id: number;
  serial_number: string;
  status: string;
  location_id: number | null;
  bin_id: number | null;
}

export interface OpeningStockLocation {
  location_id: number;
  bin_id: number | null;
  lot_id: number | null;
  serial_numbers: string[];
  quantity: string;
  unit_cost: string | null;
  value: string;
}

export interface OpeningStock {
  product_id: number;
  editable: boolean;
  entries: OpeningStockLocation[];
}

export interface OpeningStockInput {
  product_id: number;
  date?: string | null;
  entries: {
    location_id: number;
    bin_id?: number | null;
    lot_id?: number | null;
    lot_number?: string | null;
    manufactured_date?: string | null;
    expiry_date?: string | null;
    serial_numbers?: string[];
    quantity: number;
    unit_cost?: number | null;
  }[];
}

export interface Reason {
  id: number;
  name: string;
  is_system: boolean;
}
