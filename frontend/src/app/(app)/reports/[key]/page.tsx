"use client";

import { use, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, Download } from "lucide-react";
import { DatePicker, Select } from "antd";
import dayjs from "dayjs";

import { App, Button, Card, Dropdown, PageHeader, Spin } from "@/components/ui";
import { downloadReport, useReportMeta, useRunReport, type ReportParams } from "@/hooks/useReports";
import { useCurrency } from "@/hooks/useCurrency";
import { apiErrorMessage } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { ReportColumn, ReportFilter, ReportRow } from "@/types/report";

const RANGE_PRESETS = [
  { value: "today", label: "Today" },
  { value: "this_month", label: "This Month" },
  { value: "last_month", label: "Last Month" },
  { value: "this_quarter", label: "This Quarter" },
  { value: "last_quarter", label: "Last Quarter" },
  { value: "this_year", label: "This Year" },
  { value: "last_year", label: "Last Year" },
  { value: "this_fiscal_year", label: "This Fiscal Year" },
  { value: "last_fiscal_year", label: "Last Fiscal Year" },
  { value: "custom", label: "Custom" },
];

function initialParams(filters: ReportFilter[]): ReportParams {
  const params: ReportParams = {};
  for (const f of filters) {
    if (f.type === "date_range") params.range = (f.default as string) ?? "this_month";
    else if (f.type === "date") params[f.key] = dayjs().format("YYYY-MM-DD");
    else if (f.default != null) params[f.key] = f.default as string;
  }
  return params;
}

export default function ReportRunnerPage({ params }: { params: Promise<{ key: string }> }) {
  const { key } = use(params);
  const router = useRouter();
  const { money } = useCurrency();
  const { message } = App.useApp();
  const meta = useReportMeta(key);
  const [overrides, setOverrides] = useState<ReportParams>({});
  const [exporting, setExporting] = useState(false);

  const base = useMemo(
    () => (meta.data ? initialParams(meta.data.filters) : {}),
    [meta.data],
  );
  const filterValues = useMemo(() => ({ ...base, ...overrides }), [base, overrides]);

  const report = useRunReport(key, filterValues, !!meta.data);
  const set = (patch: ReportParams) => setOverrides((v) => ({ ...v, ...patch }));

  const fmt = (col: ReportColumn, row: ReportRow) => {
    const raw = row[col.key];
    if (raw === null || raw === undefined || raw === "") return "";
    if (col.type === "money") return money(Number(raw));
    if (col.type === "number") return Number(raw).toLocaleString();
    if (col.type === "date") return formatDate(String(raw));
    return String(raw);
  };

  const doExport = async (format: "pdf" | "xlsx") => {
    setExporting(true);
    try {
      await downloadReport(key, format, filterValues);
    } catch (err) {
      message.error(apiErrorMessage(err));
    } finally {
      setExporting(false);
    }
  };

  const result = report.data;
  const cols = result?.columns ?? meta.data?.columns ?? [];
  const colStyle = (c: ReportColumn) => (c.align === "right" ? "text-right" : "text-left");

  const totalRow = (row: ReportRow, strong = true) => (
    <tr className={strong ? "border-t-2 border-gray-200 font-semibold text-slate-900" : ""}>
      {cols.map((c) => (
        <td key={c.key} className={`px-3 py-2 ${colStyle(c)} tabular-nums`}>
          {fmt(c, row)}
        </td>
      ))}
    </tr>
  );

  return (
    <div className="space-y-4">
      <PageHeader
        title={meta.data?.name ?? "Report"}
        description={meta.data?.description ?? undefined}
        onBack={() => router.push("/reports")}
        actions={
          <Dropdown
            trigger={["click"]}
            menu={{
              items: [
                { key: "pdf", label: "Export PDF", onClick: () => doExport("pdf") },
                { key: "xlsx", label: "Export Excel", onClick: () => doExport("xlsx") },
              ],
            }}
          >
            <Button icon={<Download size={15} />} loading={exporting}>
              Export <ChevronDown size={14} />
            </Button>
          </Dropdown>
        }
      />

      <Card className="!p-3">
        <div className="flex flex-wrap items-end gap-3">
          {(meta.data?.filters ?? []).map((f) => (
            <Filter key={f.key} filter={f} values={filterValues} onChange={set} />
          ))}
        </div>
      </Card>

      <Card className="!p-0">
        {report.isLoading || meta.isLoading ? (
          <div className="flex min-h-[30vh] items-center justify-center">
            <Spin />
          </div>
        ) : !result ? (
          <div className="p-6 text-gray-400">Adjust the filters to run this report.</div>
        ) : (
          <div className="overflow-x-auto">
            <div className="px-4 pt-4">
              <div className="text-lg font-semibold text-slate-900">{result.title}</div>
              {result.subtitle && (
                <div className="text-sm text-gray-400">{result.subtitle}</div>
              )}
            </div>
            <table className="mt-3 w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-400">
                  {cols.map((c) => (
                    <th key={c.key} className={`px-3 pb-2 font-normal ${colStyle(c)}`}>
                      {c.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.sections.map((section, si) => (
                  <SectionRows key={si} colspan={cols.length} title={section.title}>
                    {section.rows.map((row, ri) => (
                      <tr key={ri} className="border-t border-gray-100">
                        {cols.map((c) => (
                          <td key={c.key} className={`px-3 py-1.5 ${colStyle(c)} tabular-nums`}>
                            {fmt(c, row)}
                          </td>
                        ))}
                      </tr>
                    ))}
                    {section.subtotal && totalRow(section.subtotal, false)}
                  </SectionRows>
                ))}
                {result.grand_total && totalRow(result.grand_total)}
              </tbody>
            </table>
            {result.sections.every((s) => s.rows.length === 0) && !result.grand_total && (
              <div className="p-6 text-gray-400">No data for the selected filters.</div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}

function SectionRows({
  title,
  colspan,
  children,
}: {
  title: string | null;
  colspan: number;
  children: React.ReactNode;
}) {
  return (
    <>
      {title && (
        <tr>
          <td colSpan={colspan} className="px-3 pb-1 pt-4 text-sm font-semibold text-slate-700">
            {title}
          </td>
        </tr>
      )}
      {children}
    </>
  );
}

function Filter({
  filter,
  values,
  onChange,
}: {
  filter: ReportFilter;
  values: ReportParams;
  onChange: (patch: ReportParams) => void;
}) {
  if (filter.type === "date_range") {
    const preset = (values.range as string) ?? "this_month";
    return (
      <div className="flex items-end gap-2">
        <Labeled label={filter.label}>
          <Select
            value={preset}
            onChange={(v) => onChange({ range: v, from: undefined, to: undefined })}
            options={RANGE_PRESETS}
            className="w-44"
          />
        </Labeled>
        {preset === "custom" && (
          <DatePicker.RangePicker
            format="DD MMM YYYY"
            onChange={(range) =>
              onChange({
                from: range?.[0]?.format("YYYY-MM-DD"),
                to: range?.[1]?.format("YYYY-MM-DD"),
              })
            }
          />
        )}
      </div>
    );
  }
  if (filter.type === "date") {
    const value = values[filter.key];
    return (
      <Labeled label={filter.label}>
        <DatePicker
          value={value ? dayjs(String(value)) : dayjs()}
          onChange={(d) => onChange({ [filter.key]: d ? d.format("YYYY-MM-DD") : undefined })}
          format="DD MMM YYYY"
          allowClear={false}
        />
      </Labeled>
    );
  }
  return (
    <Labeled label={filter.label}>
      <Select
        showSearch
        optionFilterProp="label"
        placeholder={`Select ${filter.label.toLowerCase()}`}
        value={values[filter.key] ?? undefined}
        onChange={(v) => onChange({ [filter.key]: v })}
        options={filter.options ?? []}
        className="w-56"
      />
    </Labeled>
  );
}

function Labeled({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-gray-400">{label}</span>
      {children}
    </label>
  );
}
