"use client";

import { Button, Card, Progress, Skeleton, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  ArrowRight,
  Building2,
  CalendarPlus,
  CheckCircle2,
  CircleAlert,
  FileCheck2,
  Plus,
  ShieldCheck,
  Users,
} from "lucide-react";
import { useRouter } from "next/navigation";
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useDashboard } from "@/hooks/useSuperAdmin";
import type { DashboardOrganization } from "@/types";

function percentage(value: number, total: number): number {
  return total ? Math.round((value / total) * 100) : 0;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}

function StatusLabel({ tone, children }: { tone: "good" | "warning" | "muted"; children: string }) {
  const dot = tone === "good" ? "bg-teal-600" : tone === "warning" ? "bg-amber-500" : "bg-slate-400";
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap text-sm text-slate-700">
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      {children}
    </span>
  );
}

function MetricCard({
  label,
  value,
  context,
  icon: Icon,
  loading,
}: {
  label: string;
  value: number;
  context: string;
  icon: typeof Building2;
  loading: boolean;
}) {
  return (
    <Card className="h-full border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.05)]">
      {loading ? (
        <Skeleton active paragraph={{ rows: 1 }} />
      ) : (
        <div>
          <div className="flex items-center justify-between gap-4">
            <div className="text-sm font-medium text-slate-500">{label}</div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-2 text-slate-600">
              <Icon size={18} />
            </div>
          </div>
          <div className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">{value}</div>
          <div className="mt-1 text-xs text-slate-500">{context}</div>
        </div>
      )}
    </Card>
  );
}

function ReadinessRow({ label, value, total }: { label: string; value: number; total: number }) {
  const percent = percentage(value, total);
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-4 text-sm">
        <span className="text-slate-600">{label}</span>
        <span className="font-medium text-slate-900">
          {value}/{total} <span className="ml-1 text-xs font-normal text-slate-400">({percent}%)</span>
        </span>
      </div>
      <Progress percent={percent} showInfo={false} strokeColor="#0f766e" trailColor="#e2e8f0" size="small" />
    </div>
  );
}

export default function DashboardPage() {
  const { data, isLoading } = useDashboard();
  const router = useRouter();
  const total = data?.organizations ?? 0;
  const active = data?.active_organizations ?? 0;
  const users = data?.organization_users ?? 0;
  const fbrEnabled = data?.fbr_enabled_organizations ?? 0;
  const taxConfigured = data?.tax_identity_organizations ?? 0;
  const missingTax = Math.max(total - taxConfigured, 0);
  const averageUsers = total ? (users / total).toFixed(1) : "0";
  const activity = (data?.activity_14d ?? []).map((point) => ({
    ...point,
    label: new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(
      new Date(`${point.date}T00:00:00`),
    ),
  }));
  const recentLogins = activity.reduce((sum, point) => sum + point.customer_logins, 0);
  const recentOrganizations = activity.reduce(
    (sum, point) => sum + point.organizations_created,
    0,
  );
  const fbrActivity = (data?.fbr_invoice_activity_14d ?? []).map((point) => ({
    ...point,
    label: new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(
      new Date(`${point.date}T00:00:00`),
    ),
  }));
  const submittedInvoices = fbrActivity.reduce((sum, point) => sum + point.submitted, 0);
  const draftInvoices = fbrActivity.reduce((sum, point) => sum + point.draft, 0);
  const failedInvoices = fbrActivity.reduce((sum, point) => sum + point.failed, 0);

  const columns: ColumnsType<DashboardOrganization> = [
    {
      title: "Organization",
      key: "organization",
      render: (_, organization) => (
        <div className="min-w-0">
          <div className="truncate font-medium text-slate-900">{organization.name}</div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span>{organization.slug}</span>
            <span>·</span>
            <span>{formatDate(organization.created_at)}</span>
          </div>
        </div>
      ),
    },
    {
      title: "Owner",
      dataIndex: "owner_email",
      render: (email: string) => <span className="text-sm text-slate-600">{email || "Not assigned"}</span>,
    },
    {
      title: "Members",
      dataIndex: "member_count",
      width: 100,
      render: (count: number) => <span className="font-medium text-slate-800">{count}</span>,
    },
    {
      title: "Tax identity",
      dataIndex: "tax_identity_configured",
      width: 130,
      render: (configured: boolean) => (
        <StatusLabel tone={configured ? "good" : "warning"}>
          {configured ? "Configured" : "Missing"}
        </StatusLabel>
      ),
    },
    {
      title: "FBR",
      key: "fbr",
      width: 120,
      render: (_, organization) => (
        <StatusLabel tone={organization.fbr_ready ? "good" : organization.fbr_enabled ? "warning" : "muted"}>
          {organization.fbr_ready ? "Ready" : organization.fbr_enabled ? "Needs setup" : "Not enabled"}
        </StatusLabel>
      ),
    },
    {
      title: "Access",
      dataIndex: "is_active",
      width: 110,
      render: (enabled: boolean) => (
        <StatusLabel tone={enabled ? "good" : "muted"}>{enabled ? "Active" : "Inactive"}</StatusLabel>
      ),
    },
  ];

  return (
    <div className="grid gap-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <Typography.Title level={2} className="!mb-1 !text-3xl">
            Platform overview
          </Typography.Title>
          <Typography.Text type="secondary">
            Monitor organization access, adoption, and launch readiness.
          </Typography.Text>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="large" onClick={() => router.push("/organizations")}>
            View organizations
          </Button>
          <Button
            type="primary"
            size="large"
            icon={<Plus size={17} />}
            onClick={() => router.push("/organizations/new")}
          >
            Create organization
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Total organizations"
          value={total}
          context={`${data?.new_organizations_30d ?? 0} created in the last 30 days`}
          icon={Building2}
          loading={isLoading}
        />
        <MetricCard
          label="Active organizations"
          value={active}
          context={`${data?.inactive_organizations ?? 0} currently inactive`}
          icon={CheckCircle2}
          loading={isLoading}
        />
        <MetricCard
          label="Organization users"
          value={users}
          context={`${averageUsers} average users per organization`}
          icon={Users}
          loading={isLoading}
        />
        <MetricCard
          label="FBR enabled"
          value={fbrEnabled}
          context={`${percentage(fbrEnabled, total)}% organization adoption`}
          icon={FileCheck2}
          loading={isLoading}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card
          title="Platform activity"
          extra={<span className="text-xs font-normal text-slate-500">Last 14 days</span>}
          className="h-full border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.05)]"
        >
          {isLoading ? (
            <Skeleton active paragraph={{ rows: 7 }} />
          ) : (
            <div className="grid gap-5">
              <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-500">
                <span>
                  <strong className="mr-1 text-sm text-slate-900">{recentLogins}</strong>
                  customer sign-ins
                </span>
                <span>
                  <strong className="mr-1 text-sm text-slate-900">{recentOrganizations}</strong>
                  new organizations
                </span>
              </div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={activity} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="#e2e8f0" />
                    <XAxis
                      dataKey="label"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: "#64748b", fontSize: 12 }}
                      minTickGap={20}
                    />
                    <YAxis
                      allowDecimals={false}
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: "#64748b", fontSize: 12 }}
                    />
                    <Tooltip
                      cursor={{ fill: "#f8fafc" }}
                      contentStyle={{
                        border: "1px solid #e2e8f0",
                        borderRadius: 8,
                        boxShadow: "0 8px 24px rgba(15, 23, 42, 0.08)",
                      }}
                    />
                    <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
                    <Area
                      type="monotone"
                      dataKey="customer_logins"
                      name="Customer sign-ins"
                      stroke="#0f766e"
                      strokeWidth={2}
                      fill="#ccfbf1"
                      fillOpacity={0.55}
                    />
                    <Bar
                      dataKey="organizations_created"
                      name="New organizations"
                      fill="#94a3b8"
                      maxBarSize={20}
                      radius={[4, 4, 0, 0]}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </Card>

        <Card
          title="FBR invoice trend"
          extra={<span className="text-xs font-normal text-slate-500">Last 14 days</span>}
          className="h-full border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.05)]"
        >
          {isLoading ? (
            <Skeleton active paragraph={{ rows: 7 }} />
          ) : (
            <div className="grid gap-5">
              <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-500">
                <span>
                  <strong className="mr-1 text-sm text-slate-900">{submittedInvoices}</strong>
                  submitted
                </span>
                <span>
                  <strong className="mr-1 text-sm text-slate-900">{draftInvoices}</strong>
                  draft
                </span>
                <span>
                  <strong className="mr-1 text-sm text-slate-900">{failedInvoices}</strong>
                  failed
                </span>
              </div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={fbrActivity}
                    margin={{ top: 8, right: 8, left: -20, bottom: 0 }}
                  >
                    <CartesianGrid vertical={false} stroke="#e2e8f0" />
                    <XAxis
                      dataKey="label"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: "#64748b", fontSize: 12 }}
                      minTickGap={20}
                    />
                    <YAxis
                      allowDecimals={false}
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: "#64748b", fontSize: 12 }}
                    />
                    <Tooltip
                      cursor={{ fill: "#f8fafc" }}
                      contentStyle={{
                        border: "1px solid #e2e8f0",
                        borderRadius: 8,
                        boxShadow: "0 8px 24px rgba(15, 23, 42, 0.08)",
                      }}
                    />
                    <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
                    <Bar
                      dataKey="draft"
                      name="Draft"
                      fill="#94a3b8"
                      maxBarSize={18}
                      radius={[4, 4, 0, 0]}
                    />
                    <Area
                      type="monotone"
                      dataKey="submitted"
                      name="Submitted"
                      stroke="#0f766e"
                      strokeWidth={2}
                      fill="#ccfbf1"
                      fillOpacity={0.5}
                    />
                    <Line
                      type="monotone"
                      dataKey="failed"
                      name="Failed"
                      stroke="#b91c1c"
                      strokeWidth={2}
                      dot={{ r: 2, fill: "#b91c1c" }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_minmax(340px,0.8fr)]">
        <Card
          title="Recent organizations"
          extra={
            <Button type="link" onClick={() => router.push("/organizations")}>
              View all <ArrowRight size={15} />
            </Button>
          }
          className="overflow-hidden border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.05)]"
          styles={{ body: { padding: 0 } }}
        >
          <Table
            rowKey="id"
            loading={isLoading}
            dataSource={data?.recent_organizations ?? []}
            columns={columns}
            pagination={false}
            scroll={{ x: 900 }}
            locale={{
              emptyText: (
                <div className="flex flex-col items-center py-12">
                  <Building2 size={28} className="text-slate-300" />
                  <div className="mt-3 font-medium text-slate-700">No organizations yet</div>
                  <div className="mt-1 text-sm text-slate-500">Create the first organization to begin.</div>
                  <Button
                    type="primary"
                    className="!mt-4"
                    icon={<Plus size={15} />}
                    onClick={() => router.push("/organizations/new")}
                  >
                    Create organization
                  </Button>
                </div>
              ),
            }}
            onRow={(organization) => ({
              onClick: () => router.push(`/organizations/${organization.id}`),
              className: "cursor-pointer",
            })}
          />
        </Card>

        <div className="grid content-start gap-6">
          <Card
            title={
              <span className="flex items-center gap-2">
                <ShieldCheck size={18} className="text-slate-600" /> Platform readiness
              </span>
            }
            className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.05)]"
          >
            {isLoading ? (
              <Skeleton active paragraph={{ rows: 5 }} />
            ) : (
              <div className="space-y-6">
                <ReadinessRow label="Active access" value={active} total={total} />
                <ReadinessRow label="Tax identity configured" value={taxConfigured} total={total} />
                <ReadinessRow label="FBR enabled" value={fbrEnabled} total={total} />
              </div>
            )}
          </Card>

          <Card
            title={
              <span className="flex items-center gap-2">
                <CircleAlert size={18} className="text-slate-600" /> Needs attention
              </span>
            }
            className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.05)]"
          >
            {isLoading ? (
              <Skeleton active paragraph={{ rows: 3 }} />
            ) : (
              <div className="divide-y divide-slate-100">
                {[
                  { label: "Inactive organizations", value: data?.inactive_organizations ?? 0 },
                  { label: "Missing tax identity", value: missingTax },
                  { label: "Incomplete FBR setup", value: data?.fbr_configuration_issues ?? 0 },
                ].map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => router.push("/organizations")}
                    className="flex w-full items-center justify-between gap-4 py-3 text-left first:pt-0 last:pb-0"
                  >
                    <span className="text-sm text-slate-600">{item.label}</span>
                    <span className="min-w-7 rounded-md bg-slate-100 px-2 py-1 text-center text-xs font-semibold text-slate-800">
                      {item.value}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </Card>

          <Card className="border-slate-200 bg-slate-950 text-white shadow-[0_1px_3px_rgba(15,23,42,0.08)]">
            <div className="flex items-start gap-3">
              <div className="rounded-lg bg-white/10 p-2.5">
                <CalendarPlus size={19} />
              </div>
              <div>
                <div className="font-semibold">Onboarding activity</div>
                <div className="mt-1 text-sm text-slate-300">
                  {data?.new_organizations_30d ?? 0} organizations created during the last 30 days.
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
