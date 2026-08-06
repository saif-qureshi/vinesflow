import type { SalespersonSummary } from "./salesperson";

export type CommissionPayoutStatus = "draft" | "submitted" | "cancelled";

export interface CommissionPayout {
  id: number;
  number: string;
  status: CommissionPayoutStatus;
  salesperson: SalespersonSummary;
  payout_date: string;
  amount: string;
  paid_through_account_id: number;
  reference: string | null;
  notes: string | null;
  created_at: string;
}

export interface CommissionPayoutInput {
  salesperson_id: number;
  payout_date?: string;
  amount: number;
  paid_through_account_id: number;
  reference?: string | null;
  notes?: string | null;
}

export interface CommissionBalance {
  salesperson: SalespersonSummary;
  earned: string;
  paid: string;
  outstanding: string;
}
