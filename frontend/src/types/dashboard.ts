export interface DashboardKpis {
  revenue: string;
  revenue_delta_pct: number | null;
  receivables: string;
  overdue: string;
  active_customers: number;
  cash_on_hand: string;
}

export interface RevenuePoint {
  month: string;
  revenue: string;
}

export interface AgingBucket {
  bucket: string;
  amount: string;
}

export interface StatusCount {
  status: string;
  invoices: number;
}

export interface RecentInvoice {
  id: number;
  number: string;
  party: string | null;
  date: string;
  amount: string;
  status: "paid" | "pending" | "overdue";
}

export interface CashFlowPoint {
  month: string;
  inflow: string;
  outflow: string;
  net: string;
}

export interface DashboardSummary {
  kpis: DashboardKpis;
  revenue_series: RevenuePoint[];
  cash_flow: CashFlowPoint[];
  aging: AgingBucket[];
  invoice_status: StatusCount[];
  recent_invoices: RecentInvoice[];
}
