export type ReportFilterType = "date_range" | "date" | "select" | "text";
export type ReportColumnType = "text" | "money" | "number" | "date";

export interface ReportListItem {
  key: string;
  name: string;
  category: string;
  description: string | null;
}

export interface ReportFilterOption {
  value: string | number;
  label: string;
}

export interface ReportFilter {
  key: string;
  type: ReportFilterType;
  label: string;
  required: boolean;
  default: string | null;
  options: ReportFilterOption[] | null;
  source: string | null;
}

export interface ReportOperator {
  value: string;
  label: string;
}

export interface ReportColumn {
  key: string;
  label: string;
  type: ReportColumnType;
  align: "left" | "right";
  aggregate?: string;
  operators?: ReportOperator[];
}

export interface ReportColumnFilter {
  id: number;
  field?: string;
  op?: string;
  value?: string | number;
  value2?: string | number;
}

export type ReportRow = Record<string, string | number | null>;

export interface ReportSection {
  title: string | null;
  rows: ReportRow[];
  subtotal: ReportRow | null;
}

export interface ReportResult {
  key: string;
  title: string;
  subtitle: string | null;
  columns: ReportColumn[];
  sections: ReportSection[];
  grand_total: ReportRow | null;
}

export interface ReportMeta {
  key: string;
  name: string;
  category: string;
  description: string | null;
  supports_filters: boolean;
  filters: ReportFilter[];
  columns: ReportColumn[];
}
