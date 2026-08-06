import type { CategorySummary } from "./category";
import type { Media, MediaInput } from "./media";

export interface NamedRecord {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface NamedRecordInput {
  name: string;
  description?: string | null;
  is_active?: boolean;
}

export interface NamedSummary {
  id: number;
  name: string;
}
import type { UomSummary } from "./uom";

export type ProductNature = "good" | "service";
export type ProductType = "single" | "variable";
export type TrackingMode = "none" | "lot" | "serial";

export interface VariantAttribute {
  name: string;
  options: string[];
}

export interface AttributeValueSummary {
  id: number;
  attribute_id: number;
  attribute_name: string;
  value: string;
}

export interface ProductVariant {
  id: number;
  name: string;
  values: AttributeValueSummary[];
  sku: string | null;
  barcode: string | null;
  sale_price: number | null;
  purchase_price: number | null;
  is_active: boolean;
}

export interface VariantInput {
  id?: number | null;
  options: Record<string, string>;
  name?: string;
  sku?: string | null;
  barcode?: string | null;
  sale_price?: number | null;
  purchase_price?: number | null;
  is_active?: boolean;
}

export interface Product {
  id: number;
  name: string;
  description: string | null;
  nature: ProductNature;
  type: ProductType;
  sku: string | null;
  barcode: string | null;
  sale_price: number | null;
  purchase_price: number | null;
  track_inventory: boolean;
  tracking_mode: TrackingMode;
  reorder_point: number | null;
  is_active: boolean;
  hs_code: string | null;
  uom_code: string | null;
  sale_type_code: string | null;
  tax_rate_code: string | null;
  sro_schedule_code: string | null;
  sro_item_serial: string | null;
  category: CategorySummary | null;
  uom: UomSummary | null;
  brand: NamedSummary | null;
  manufacturer: NamedSummary | null;
  media: Media[];
  variant_attributes: VariantAttribute[];
  variants: ProductVariant[];
  created_at: string;
}

export interface ProductInput {
  name: string;
  description?: string | null;
  nature: ProductNature;
  type: ProductType;
  sku?: string | null;
  barcode?: string | null;
  category_id?: number | null;
  uom_id?: number | null;
  sale_price?: number | null;
  purchase_price?: number | null;
  track_inventory: boolean;
  tracking_mode: TrackingMode;
  reorder_point?: number | null;
  hs_code?: string | null;
  uom_code?: string | null;
  sale_type_code?: string | null;
  tax_rate_code?: string | null;
  sro_schedule_code?: string | null;
  sro_item_serial?: string | null;
  brand_id?: number | null;
  manufacturer_id?: number | null;
  media?: MediaInput[];
  variant_attributes?: VariantAttribute[];
  variants?: VariantInput[];
}
