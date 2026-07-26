"use client";

import { Plus, Trash2 } from "lucide-react";
import type { ColumnsType } from "antd/es/table";

import { App, Button, Card, DataTable, PageHeader, Popconfirm, Switch, Tag } from "@/components/ui";
import {
  useCreateFiscalYear,
  useDeleteFiscalYear,
  useFiscalYears,
  usePeriods,
  useSetPeriodStatus,
} from "@/hooks/useAccounting";
import { apiErrorMessage } from "@/lib/api";
import type { AccountingPeriod, PeriodStatus } from "@/types";

const STATUS_COLOR: Record<PeriodStatus, string> = {
  open: "green",
  locked: "gold",
  closed: "default",
};

function fmt(date: string) {
  return new Date(date).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// The label the backend will give the next fiscal year (the one after `endsOn`).
function nextYearLabel(endsOn: string): string {
  const [y, m, d] = endsOn.split("-").map(Number);
  const start = new Date(y, m - 1, d + 1);
  const startY = start.getFullYear();
  const endY = new Date(startY + 1, start.getMonth(), start.getDate() - 1).getFullYear();
  return startY !== endY ? `FY ${startY}-${String(endY).slice(-2)}` : `FY ${startY}`;
}

export default function FiscalPeriodsPage() {
  const { message } = App.useApp();
  const fiscalYears = useFiscalYears();
  const periods = usePeriods();
  const setStatus = useSetPeriodStatus();
  const createYear = useCreateFiscalYear();
  const deleteYear = useDeleteFiscalYear();

  const years = fiscalYears.data ?? [];
  const nextLabel = years.length ? nextYearLabel(years[years.length - 1].ends_on) : null;

  const addYear = async () => {
    try {
      const res = await createYear.mutateAsync();
      message.success(`Created ${res.data.name}`);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const removeYear = async (id: number, name: string) => {
    try {
      await deleteYear.mutateAsync(id);
      message.success(`Deleted ${name}`);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const toggle = async (period: AccountingPeriod, lock: boolean) => {
    try {
      await setStatus.mutateAsync({ id: period.id, status: lock ? "locked" : "open" });
      message.success(lock ? "Period locked" : "Period reopened");
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const columns: ColumnsType<AccountingPeriod> = [
    { title: "Period", dataIndex: "name", key: "name", render: (v) => <span className="font-medium">{v}</span> },
    {
      title: "Range",
      key: "range",
      render: (_, p) => (
        <span className="text-slate-500">
          {fmt(p.starts_on)} – {fmt(p.ends_on)}
        </span>
      ),
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 110,
      render: (s: PeriodStatus) => <Tag color={STATUS_COLOR[s]}>{s}</Tag>,
    },
    {
      title: "Locked",
      key: "lock",
      width: 100,
      align: "right",
      render: (_, p) => (
        <Switch
          checked={p.status !== "open"}
          disabled={p.status === "closed" || setStatus.isPending}
          onChange={(checked) => toggle(p, checked)}
        />
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Fiscal Periods"
        description="Lock a period to stop new postings landing in it"
        actions={
          <Popconfirm
            title={nextLabel ? `Create ${nextLabel}?` : "Create the next fiscal year?"}
            description="This adds a new fiscal year and its 12 monthly periods."
            okText="Create"
            onConfirm={addYear}
            disabled={fiscalYears.isLoading}
          >
            <Button type="primary" icon={<Plus size={16} />} loading={createYear.isPending}>
              New fiscal year
            </Button>
          </Popconfirm>
        }
      />
      {(fiscalYears.data ?? []).map((fy) => (
        <Card
          key={fy.id}
          title={
            <span className="flex items-center gap-2">
              {fy.name}
              <span className="text-xs font-normal text-slate-400">
                {fmt(fy.starts_on)} – {fmt(fy.ends_on)}
              </span>
              <Tag color={fy.status === "active" ? "green" : "default"}>{fy.status}</Tag>
            </span>
          }
          extra={
            years.length > 1 ? (
              <Popconfirm
                title={`Delete ${fy.name}?`}
                description="Removes the year and its periods. Only allowed if nothing has posted to it."
                okText="Delete"
                okButtonProps={{ danger: true }}
                onConfirm={() => removeYear(fy.id, fy.name)}
              >
                <Button size="small" type="text" danger icon={<Trash2 size={15} />} />
              </Popconfirm>
            ) : null
          }
        >
          <DataTable<AccountingPeriod>
            rowKey="id"
            columns={columns}
            dataSource={(periods.data ?? []).filter((p) => p.fiscal_year_id === fy.id)}
            loading={periods.isLoading || fiscalYears.isLoading}
            pagination={false}
          />
        </Card>
      ))}
    </div>
  );
}
