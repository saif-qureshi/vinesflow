export type AccountType = "asset" | "liability" | "equity" | "income" | "expense";
export type NormalBalance = "debit" | "credit";
export type FiscalYearStatus = "active" | "closed";
export type PeriodStatus = "open" | "locked" | "closed";

export interface Account {
  id: number;
  parent_id: number | null;
  code: string;
  name: string;
  account_type: AccountType;
  normal_balance: NormalBalance;
  is_control_account: boolean;
  is_postable: boolean;
  is_active: boolean;
  description: string | null;
}

export interface AccountInput {
  code: string;
  name: string;
  account_type: AccountType;
  normal_balance: NormalBalance;
  parent_id?: number | null;
  is_postable?: boolean;
  description?: string | null;
}

export interface AccountUpdateInput {
  name?: string;
  parent_id?: number | null;
  is_active?: boolean;
  description?: string | null;
}

export interface FiscalYear {
  id: number;
  name: string;
  starts_on: string;
  ends_on: string;
  status: FiscalYearStatus;
}

export interface AccountingPeriod {
  id: number;
  fiscal_year_id: number;
  name: string;
  period_no: number;
  starts_on: string;
  ends_on: string;
  status: PeriodStatus;
}
