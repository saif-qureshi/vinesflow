"use client";

import { use, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, Download, SlidersHorizontal } from "lucide-react";
import { DatePicker, Select } from "antd";
import dayjs from "dayjs";

import { App, Button, Card, Dropdown, PageHeader, Spin } from "@/components/ui";
import { downloadReport, useReportMeta, useRunReport, type ReportParams } from "@/hooks/useReports";
import { useCurrency } from "@/hooks/useCurrency";
import { apiErrorMessage } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { ReportColumn, ReportFilter, ReportRow } from "@/types/report";
import { ColumnFilters, type BuiltFilter } from "../ColumnFilters";

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
  const [advanced, setAdvanced] = useState<BuiltFilter[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [exporting, setExporting] = useState(false);

  const base = useMemo(() => (meta.data ? initialParams(meta.data.filters) : {}), [meta.data]);
  const filterValues = useMemo<ReportParams>(
    () => ({
      ...base,
      ...overrides,
      filters: advanced.length ? JSON.stringify(advanced) : undefined,
    }),
    [base, overrides, advanced],
  );

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
  const alignClass = (c: ReportColumn) => (c.align === "right" ? "text-right" : "text-left");
  const rowCount = result?.sections.reduce((n, s) => n + s.rows.length, 0) ?? 0;

  return (
    <div className="space-y-4">
      <PageHeader
        title={meta.data?.name ?? "Report"}
        description={meta.data?.description ?? undefined}
        onBack={() => router.push("/reports")}
        actions={
          <div className="flex items-center gap-2">
            {meta.data?.supports_filters && (
              <Button
                icon={<SlidersHorizontal size={15} />}
                type={showFilters || advanced.length ? "primary" : "default"}
                ghost={showFilters || advanced.length > 0}
                onClick={() => setShowFilters((s) => !s)}
              >
                Filters{advanced.length ? ` (${advanced.length})` : ""}
              </Button>
            )}
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
          </div>
        }
      />

      <Card size="small" className="!rounded-xl">
        <div className="flex flex-wrap items-end gap-3">
          {(meta.data?.filters ?? []).map((f) => (
            <Filter key={f.key} filter={f} values={filterValues} onChange={set} />
          ))}
        </div>
        {meta.data?.supports_filters && showFilters && (
          <div className="mt-3 border-t border-gray-100 pt-3">
            <div className="mb-2 text-xs font-medium text-gray-400">Filter by column</div>
            <ColumnFilters columns={meta.data.columns} onApply={setAdvanced} />
          </div>
        )}
      </Card>

      <Card className="!rounded-xl !p-0">
        {report.isLoading || meta.isLoading ? (
          <div className="flex min-h-[40vh] items-center justify-center">
            <Spin />
          </div>
        ) : !result ? (
          <div className="p-8 text-center text-gray-400">Adjust the filters to run this report.</div>
        ) : (
          <>
            <div className="flex items-start justify-between gap-3 border-b border-gray-100 px-5 py-4">
              <div>
                <div className="text-base font-semibold text-slate-900">{result.title}</div>
                {result.subtitle && (
                  <div className="mt-0.5 text-xs text-gray-400">{result.subtitle}</div>
                )}
              </div>
              <span className="whitespace-nowrap pt-1 text-xs text-gray-400">
                {rowCount} {rowCount === 1 ? "row" : "rows"}
              </span>
            </div>

            <div className="max-h-[68vh] overflow-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-10 bg-white">
                  <tr className="text-xs text-gray-400">
                    {cols.map((c) => (
                      <th
                        key={c.key}
                        className={`border-b border-gray-100 px-5 py-2.5 font-medium uppercase tracking-wide ${alignClass(c)}`}
                      >
                        {c.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.sections.map((section, si) => (
                    <SectionRows key={si} colspan={cols.length} title={section.title}>
                      {section.rows.map((row, ri) => (
                        <tr key={ri} className="border-b border-gray-50 hover:bg-slate-50/60">
                          {cols.map((c) => (
                            <td key={c.key} className={`px-5 py-2 ${alignClass(c)} tabular-nums`}>
                              {fmt(c, row)}
                            </td>
                          ))}
                        </tr>
                      ))}
                      {section.subtotal && (
                        <tr className="border-t border-gray-200 font-medium text-slate-800">
                          {cols.map((c) => (
                            <td key={c.key} className={`px-5 py-2 ${alignClass(c)} tabular-nums`}>
                              {fmt(c, section.subtotal!)}
                            </td>
                          ))}
                        </tr>
                      )}
                    </SectionRows>
                  ))}
                  {result.grand_total && (
                    <tr className="border-t-2 border-slate-300 bg-slate-50 font-semibold text-slate-900">
                      {cols.map((c) => (
                        <td key={c.key} className={`px-5 py-2.5 ${alignClass(c)} tabular-nums`}>
                          {fmt(c, result.grand_total!)}
                        </td>
                      ))}
                    </tr>
                  )}
                </tbody>
              </table>
              {rowCount === 0 && !result.grand_total && (
                <div className="p-8 text-center text-gray-400">
                  No data for the selected filters.
                </div>
              )}
            </div>
          </>
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
        <tr className="bg-slate-50/40">
          <td colSpan={colspan} className="px-5 pb-1.5 pt-4 text-sm font-semibold text-slate-700">
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
