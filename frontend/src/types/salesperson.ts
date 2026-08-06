export interface Salesperson {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  commission_rate: string;
  is_active: boolean;
  created_at: string;
}

export interface SalespersonInput {
  name?: string;
  email?: string | null;
  phone?: string | null;
  commission_rate?: number;
  is_active?: boolean;
}

export interface SalespersonSummary {
  id: number;
  name: string;
}
