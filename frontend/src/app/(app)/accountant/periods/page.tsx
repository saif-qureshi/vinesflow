"use client";

import type { ColumnsType } from "antd/es/table";

import { App, Card, DataTable, PageHeader, Switch, Tag } from "@/components/ui";
import { useFiscalYears, usePeriods, useSetPeriodStatus } from "@/hooks/useAccounting";
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

export default function FiscalPeriodsPage() {
  const { message } = App.useApp();
  const fiscalYears = useFiscalYears();
  const periods = usePeriods();
  const setStatus = useSetPeriodStatus();

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
