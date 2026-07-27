export type ExpenseStatus = "draft" | "submitted" | "cancelled";

export interface ExpenseParty {
  id: number;
  name: string;
}

export interface ExpenseLine {
  id: number;
  account_id: number;
  line_no: number;
  description: string | null;
  amount: string;
}

export interface ExpenseRecord {
  id: number;
  number: string;
  status: ExpenseStatus;
  expense_date: string;
  paid_through_account_id: number;
  vendor_id: number | null;
  vendor_name: string | null;
  vendor: ExpenseParty | null;
  customer_id: number | null;
  is_tax_inclusive: boolean;
  reference_no: string | null;
  notes: string | null;
  subtotal: string;
  tax_amount: string;
  total: string;
  submitted_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  lines: ExpenseLine[];
}

export interface ExpenseSummary {
  id: number;
  number: string;
  status: ExpenseStatus;
  expense_date: string;
  vendor_name: string | null;
  reference_no: string | null;
  total: string;
}

export interface ExpenseLineInput {
  account_id: number;
  description?: string | null;
  amount: number;
}

export interface ExpenseInput {
  expense_date?: string | null;
  paid_through_account_id: number;
  vendor_id?: number | null;
  customer_id?: number | null;
  is_tax_inclusive?: boolean;
  tax_amount?: number;
  reference_no?: string | null;
  notes?: string | null;
  lines: ExpenseLineInput[];
}
