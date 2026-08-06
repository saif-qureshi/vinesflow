"use client";

import { Spin, Table } from "antd";
import { ArrowDownRight, ArrowUpRight, Banknote, Landmark, TriangleAlert, Wallet } from "lucide-react";

import { useAppTheme, useSession } from "@/hooks/useSession";
import { useCurrency } from "@/hooks/useCurrency";
import { useDashboard } from "@/hooks/useDashboard";
import { Card, Col, PageHeader, Row, Tag, Typography } from "@/components/ui";
import { AgingChart, CashFlowChart, RevenueChart, StatusChart } from "@/components/dashboard/charts";
import { formatDate } from "@/lib/format";
import type { RecentInvoice } from "@/types/dashboard";

const STATUS_COLOR: Record<RecentInvoice["status"], string> = { paid: "green", pending: "gold", overdue: "red" };

function KpiTile({
  title,
  value,
  delta,
  up,
  good,
  icon,
}: {
  title: string;
  value: string;
  delta?: string | null;
  up?: boolean;
  good?: boolean;
  icon: React.ReactNode;
}) {
  const { accent } = useAppTheme();
  return (
    <Card styles={{ body: { padding: 18 } }} className="border-gray-100">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm text-gray-500">{title}</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
          {delta != null && (
            <div className="mt-1 flex items-center gap-1 text-xs font-medium" style={{ color: good ? "#16a34a" : "#dc2626" }}>
              {up ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
              {delta} vs last month
            </div>
          )}
        </div>
        <div className="flex h-11 w-11 items-center justify-center rounded-xl" style={{ backgroundColor: `${accent}14`, color: accent }}>
          {icon}
        </div>
      </div>
    </Card>
  );
}

export default function DashboardPage() {
  const { currentMembership } = useSession();
  const { money, compact } = useCurrency();
  const { data, isLoading } = useDashboard();

  const kpis = data?.kpis;
  const deltaPct = kpis?.revenue_delta_pct ?? null;
  const metrics = [
    {
      title: "Revenue (this month)",
      value: compact(Number(kpis?.revenue ?? 0)),
      delta: deltaPct != null ? `${Math.abs(deltaPct)}%` : null,
      up: (deltaPct ?? 0) >= 0,
      good: (deltaPct ?? 0) >= 0,
      icon: <Banknote size={20} />,
    },
    { title: "Cash on hand", value: compact(Number(kpis?.cash_on_hand ?? 0)), icon: <Landmark size={20} /> },
    { title: "Receivables", value: compact(Number(kpis?.receivables ?? 0)), icon: <Wallet size={20} /> },
    { title: "Overdue", value: compact(Number(kpis?.overdue ?? 0)), icon: <TriangleAlert size={20} /> },
  ];

  const revenueData = (data?.revenue_series ?? []).map((p) => ({ month: p.month, revenue: Number(p.revenue) }));
  const cashFlowData = (data?.cash_flow ?? []).map((p) => ({
    month: p.month,
    inflow: Number(p.inflow),
    outflow: Number(p.outflow),
  }));
  const agingData = (data?.aging ?? []).map((a) => ({ bucket: a.bucket, amount: Number(a.amount) }));
  const statusData = data?.invoice_status ?? [];
  const recent = (data?.recent_invoices ?? []).map((r) => ({
    key: String(r.id),
    number: r.number,
    customer: r.party ?? "—",
    date: r.date,
    amount: Number(r.amount),
    status: r.status,
  }));

  const columns = [
    { title: "Invoice", dataIndex: "number", key: "number", render: (v: string) => <span className="font-mono text-sm">{v}</span> },
    { title: "Customer", dataIndex: "customer", key: "customer", render: (v: string) => <span className="font-medium">{v}</span> },
    { title: "Issued", dataIndex: "date", key: "date", render: (v: string) => <span className="text-gray-500">{formatDate(v)}</span> },
    { title: "Amount", dataIndex: "amount", key: "amount", align: "right" as const, render: (v: number) => <span className="font-mono tabular-nums">{money(v)}</span> },
    { title: "Status", dataIndex: "status", key: "status", render: (s: RecentInvoice["status"]) => <Tag color={STATUS_COLOR[s]} className="capitalize">{s}</Tag> },
  ];

  return (
    <div className="space-y-5">
      <PageHeader
        title="Overview"
        description={
          <>
            {currentMembership?.organization.name} · {currentMembership?.organization.currency}
          </>
        }
      />

      {isLoading ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <Spin size="large" />
        </div>
      ) : (
        <>
          <Row gutter={[16, 16]}>
            {metrics.map((m) => (
              <Col key={m.title} xs={24} sm={12} lg={6}>
                <KpiTile {...m} />
              </Col>
            ))}
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} lg={16}>
              <Card title="Revenue" extra={<Typography.Text type="secondary" className="text-xs">Last 6 months</Typography.Text>} className="border-gray-100">
                <RevenueChart data={revenueData} />
              </Card>
            </Col>
            <Col xs={24} lg={8}>
              <Card title="Invoice status" extra={<Typography.Text type="secondary" className="text-xs">Filed invoices</Typography.Text>} className="h-full border-gray-100">
                <StatusChart data={statusData} />
              </Card>
            </Col>
          </Row>

          <Card
            title="Cash flow"
            extra={
              <Typography.Text type="secondary" className="text-xs">
                Money in and out of cash and bank accounts
              </Typography.Text>
            }
            className="border-gray-100"
          >
            <CashFlowChart data={cashFlowData} />
          </Card>

          <Card title="Receivables aging" extra={<Typography.Text type="secondary" className="text-xs">Outstanding by age</Typography.Text>} className="border-gray-100">
            <AgingChart data={agingData} />
          </Card>

          <Card title="Recent invoices" extra={<Typography.Text type="secondary" className="text-xs">Latest 5</Typography.Text>} className="border-gray-100">
            <Table size="middle" columns={columns} dataSource={recent} pagination={false} locale={{ emptyText: "No invoices yet" }} />
          </Card>
        </>
      )}
    </div>
  );
}
