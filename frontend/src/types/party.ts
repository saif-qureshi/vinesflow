export type PartyRole = "customer" | "vendor";
export type PartyType = "business" | "individual";

export interface Address {
  attention?: string | null;
  line1?: string | null;
  line2?: string | null;
  city?: string | null;
  state?: string | null;
  country?: string | null;
  postal_code?: string | null;
  phone?: string | null;
}

export interface Party {
  id: number;
  is_customer: boolean;
  is_vendor: boolean;
  type: PartyType;
  name: string;
  avatar_key: string | null;
  avatar_url: string | null;
  company_name: string | null;
  salutation: string | null;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  work_phone: string | null;
  mobile: string | null;
  currency: string | null;
  ntn: string | null;
  strn: string | null;
  cnic: string | null;
  payment_term_days: number | null;
  billing_address: Address | null;
  shipping_address: Address | null;
  notes: string | null;
  is_active: boolean;
  balance: string;
  created_at: string;
}

export interface PartyInput {
  type: PartyType;
  is_customer?: boolean;
  is_vendor?: boolean;
  name: string;
  avatar_key?: string | null;
  company_name?: string | null;
  salutation?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  email?: string | null;
  work_phone?: string | null;
  mobile?: string | null;
  currency?: string | null;
  ntn?: string | null;
  strn?: string | null;
  cnic?: string | null;
  payment_term_days?: number | null;
  billing_address?: Address | null;
  shipping_address?: Address | null;
  notes?: string | null;
  is_active?: boolean;
}
