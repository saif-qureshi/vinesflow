"use client";

import { Button, Card, Col, Progress, Row, Skeleton, Typography } from "antd";
import { ArrowRight, Building2, CircleCheck, CircleOff, Plus, Users } from "lucide-react";
import { useRouter } from "next/navigation";

import { useDashboard } from "@/hooks/useSuperAdmin";

const cards = [
  { key: "organizations", title: "Organizations", icon: Building2, color: "text-teal-700" },
  { key: "active_organizations", title: "Active", icon: CircleCheck, color: "text-emerald-600" },
  { key: "inactive_organizations", title: "Inactive", icon: CircleOff, color: "text-amber-600" },
  { key: "organization_users", title: "Organization users", icon: Users, color: "text-violet-600" },
] as const;

export default function DashboardPage() {
  const { data, isLoading } = useDashboard();
  const router = useRouter();
  const activePercent = data?.organizations
    ? Math.round((data.active_organizations / data.organizations) * 100)
    : 0;

  return (
    <div>
      <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <Typography.Title level={2} className="!mb-1 !text-3xl">
            Dashboard
          </Typography.Title>
          <Typography.Text type="secondary">
            A current overview of Vineflow organizations.
          </Typography.Text>
        </div>
        <Button
          type="primary"
          icon={<Plus size={17} />}
          onClick={() => router.push("/organizations/new")}
        >
          New organization
        </Button>
      </div>
      <Row gutter={[16, 16]}>
        {cards.map(({ key, title, icon: Icon, color }) => (
          <Col xs={24} sm={12} xl={6} key={key}>
            <Card className="h-full border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]">
              {isLoading ? (
                <Skeleton active paragraph={{ rows: 1 }} />
              ) : (
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-sm text-slate-500">{title}</div>
                    <div className="mt-2 text-3xl font-semibold text-slate-900">
                      {data?.[key] ?? 0}
                    </div>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                    <Icon size={22} className={color} />
                  </div>
                </div>
              )}
            </Card>
          </Col>
        ))}
      </Row>

      <Card className="mt-6 border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="w-full max-w-xl">
            <div className="mb-1 text-base font-semibold text-slate-900">Organization health</div>
            <div className="mb-4 text-sm text-slate-500">
              {data?.active_organizations ?? 0} of {data?.organizations ?? 0} organizations are active.
            </div>
            {isLoading ? (
              <Skeleton active paragraph={{ rows: 1 }} title={false} />
            ) : (
              <Progress percent={activePercent} strokeColor="#0f766e" trailColor="#e2e8f0" />
            )}
          </div>
          <Button onClick={() => router.push("/organizations")}>
            Manage organizations <ArrowRight size={16} />
          </Button>
        </div>
      </Card>
    </div>
  );
}
