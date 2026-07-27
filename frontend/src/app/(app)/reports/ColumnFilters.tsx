"use client";

import { useState } from "react";
import { DatePicker, Input, InputNumber, Select } from "antd";
import { Plus, X } from "lucide-react";
import dayjs from "dayjs";

import { Button } from "@/components/ui";
import type { ReportColumn, ReportColumnFilter } from "@/types/report";

export type BuiltFilter = { field: string; op: string; value: string | number | string[] };

let _id = 1;

function typeOf(columns: ReportColumn[], field?: string) {
  const col = columns.find((c) => c.key === field);
  if (!col) return "text";
  if (col.type === "money" || col.type === "number") return "number";
  if (col.type === "date") return "date";
  return "text";
}

function build(rows: ReportColumnFilter[]): BuiltFilter[] {
  const out: BuiltFilter[] = [];
  for (const r of rows) {
    if (!r.field || !r.op) continue;
    if (r.op === "between") {
      if (r.value === undefined || r.value2 === undefined) continue;
      out.push({ field: r.field, op: r.op, value: [String(r.value), String(r.value2)] });
    } else if (r.value !== undefined && r.value !== "") {
      out.push({ field: r.field, op: r.op, value: r.value });
    }
  }
  return out;
}

export function ColumnFilters({
  columns,
  onApply,
}: {
  columns: ReportColumn[];
  onApply: (filters: BuiltFilter[]) => void;
}) {
  const [rows, setRows] = useState<ReportColumnFilter[]>([{ id: _id++ }]);

  const fields = columns.filter((c) => c.key && c.operators?.length);
  const fieldOptions = fields.map((c) => ({ value: c.key, label: c.label }));

  const patch = (id: number, next: Partial<ReportColumnFilter>) =>
    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, ...next } : r)));
  const add = () => setRows((rs) => [...rs, { id: _id++ }]);
  const remove = (id: number) =>
    setRows((rs) => (rs.length > 1 ? rs.filter((r) => r.id !== id) : rs));

  const apply = () => onApply(build(rows));
  const clear = () => {
    setRows([{ id: _id++ }]);
    onApply([]);
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-slate-50/60 p-3">
      <div className="space-y-2">
        {rows.map((row) => {
          const col = columns.find((c) => c.key === row.field);
          const kind = typeOf(columns, row.field);
          return (
            <div key={row.id} className="flex flex-wrap items-center gap-2">
              <Select
                placeholder="Column"
                value={row.field}
                onChange={(field) =>
                  patch(row.id, { field, op: undefined, value: undefined, value2: undefined })
                }
                options={fieldOptions}
                style={{ width: 190 }}
                showSearch
                optionFilterProp="label"
              />
              <Select
                placeholder="Condition"
                value={row.op}
                onChange={(op) => patch(row.id, { op, value: undefined, value2: undefined })}
                options={col?.operators ?? []}
                style={{ width: 170 }}
                disabled={!row.field}
              />
              <ValueInput kind={kind} row={row} onChange={(v) => patch(row.id, v)} />
              <Button
                type="text"
                icon={<X size={15} />}
                onClick={() => remove(row.id)}
                aria-label="Remove condition"
                className="!text-gray-400"
              />
            </div>
          );
        })}
      </div>

      <div className="mt-2 flex items-center gap-2">
        <Button type="dashed" size="small" icon={<Plus size={13} />} onClick={add}>
          Add condition
        </Button>
        <div className="ml-auto flex items-center gap-2">
          <Button size="small" onClick={clear}>
            Clear
          </Button>
          <Button type="primary" size="small" onClick={apply}>
            Apply filters
          </Button>
        </div>
      </div>
    </div>
  );
}

function ValueInput({
  kind,
  row,
  onChange,
}: {
  kind: string;
  row: ReportColumnFilter;
  onChange: (v: Partial<ReportColumnFilter>) => void;
}) {
  if (!row.op) return <span className="text-xs text-gray-300">value</span>;
  const between = row.op === "between";

  if (kind === "number") {
    return between ? (
      <span className="flex items-center gap-1">
        <InputNumber
          placeholder="Min"
          value={row.value as number}
          onChange={(v) => onChange({ value: v ?? undefined })}
          style={{ width: 110 }}
        />
        <span className="text-gray-400">–</span>
        <InputNumber
          placeholder="Max"
          value={row.value2 as number}
          onChange={(v) => onChange({ value2: v ?? undefined })}
          style={{ width: 110 }}
        />
      </span>
    ) : (
      <InputNumber
        placeholder="Value"
        value={row.value as number}
        onChange={(v) => onChange({ value: v ?? undefined })}
        style={{ width: 180 }}
      />
    );
  }
  if (kind === "date") {
    return between ? (
      <DatePicker.RangePicker
        format="DD MMM YYYY"
        onChange={(r) =>
          onChange({ value: r?.[0]?.format("YYYY-MM-DD"), value2: r?.[1]?.format("YYYY-MM-DD") })
        }
      />
    ) : (
      <DatePicker
        format="DD MMM YYYY"
        value={row.value ? dayjs(String(row.value)) : undefined}
        onChange={(d) => onChange({ value: d ? d.format("YYYY-MM-DD") : undefined })}
        style={{ width: 180 }}
      />
    );
  }
  return (
    <Input
      placeholder="Value"
      value={row.value as string}
      onChange={(e) => onChange({ value: e.target.value })}
      style={{ width: 220 }}
    />
  );
}
