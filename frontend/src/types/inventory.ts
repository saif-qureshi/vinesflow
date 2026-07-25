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

export interface InventoryItem {
  id: number;
  name: string;
  sku: string | null;
  is_variant: boolean;
  uom_symbol: string | null;
  reorder_point: number | null;
  on_hand: string;
  is_low: boolean;
}

export interface StockMovement {
  id: number;
  product_id: number;
  location_id: number;
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
}

export interface Reason {
  id: number;
  name: string;
  is_system: boolean;
}
