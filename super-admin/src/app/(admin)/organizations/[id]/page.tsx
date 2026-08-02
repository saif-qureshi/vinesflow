"use client";

import { Button, Card, Descriptions, Result, Space, Spin, Tag, Typography } from "antd";
import { ArrowLeft, Building2, CalendarDays, Edit3, Mail, Users } from "lucide-react";
import { useParams, useRouter } from "next/navigation";

import { useOrganization } from "@/hooks/useSuperAdmin";

const monthNames = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export default function OrganizationViewPage() {
  const params = useParams<{ id: string }>();
  const organizationId = Number(params.id);
  const { data: organization, isLoading, isError } = useOrganization(organizationId);
  const router = useRouter();

  if (isLoading) {
    return <div className="flex min-h-80 items-center justify-center"><Spin size="large" /></div>;
  }
  if (isError || !organization) {
    return <Result status="404" title="Organization not found" />;
  }

  return (
    <div>
      <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div className="flex items-start gap-3">
          <Button
            type="text"
            icon={<ArrowLeft size={19} />}
            onClick={() => router.push("/organizations")}
            aria-label="Back to organizations"
          />
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <Typography.Title level={2} className="!mb-0 !text-3xl">
                {organization.name}
              </Typography.Title>
              <Tag color={organization.is_active ? "green" : "default"}>
                {organization.is_active ? "Active" : "Inactive"}
              </Tag>
            </div>
            <Typography.Text type="secondary">{organization.slug}</Typography.Text>
          </div>
        </div>
        <Button
          type="primary"
          icon={<Edit3 size={17} />}
          onClick={() => router.push(`/organizations/${organization.id}/edit`)}
        >
          Edit organization
        </Button>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <Card
          title={
            <Space>
              <Building2 size={18} />
              Organization details
            </Space>
          }
          className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]"
        >
          <Descriptions column={{ xs: 1, sm: 2, lg: 3 }} layout="vertical">
            <Descriptions.Item label="Organization name">{organization.name}</Descriptions.Item>
            <Descriptions.Item label="Industry">{organization.industry || "—"}</Descriptions.Item>
            <Descriptions.Item label="Country">{organization.country}</Descriptions.Item>
            <Descriptions.Item label="Currency">{organization.currency}</Descriptions.Item>
            <Descriptions.Item label="Fiscal year starts">
              {monthNames[organization.fiscal_year_start_month - 1]}
            </Descriptions.Item>
            <Descriptions.Item label="Created">
              {new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
                new Date(organization.created_at),
              )}
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <div className="grid gap-6">
          <Card
            title={
              <Space>
                <Users size={18} />
                Owner and members
              </Space>
            }
            className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]"
          >
            <div className="font-medium text-slate-900">{organization.owner_name || "Owner"}</div>
            <div className="mt-2 flex items-center gap-2 text-sm text-slate-500">
              <Mail size={15} /> {organization.owner_email}
            </div>
            <div className="mt-4 flex items-center gap-2 text-sm text-slate-600">
              <Users size={15} /> {organization.member_count} member
              {organization.member_count === 1 ? "" : "s"}
            </div>
          </Card>
          <Card className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-teal-50 p-3 text-teal-700">
                <CalendarDays size={20} />
              </div>
              <div>
                <div className="text-sm text-slate-500">Organization ID</div>
                <div className="font-semibold text-slate-900">#{organization.id}</div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
