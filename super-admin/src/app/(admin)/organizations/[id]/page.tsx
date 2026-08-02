"use client";

import { useState } from "react";

import {
  App,
  Avatar,
  Button,
  Card,
  Descriptions,
  Result,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  ArrowLeft,
  Ban,
  Building2,
  CalendarDays,
  CheckCircle2,
  Edit3,
  FileCheck2,
  KeyRound,
  MapPin,
  PlayCircle,
  ShieldCheck,
  Users,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";

import { useOrganization, useSetOrganizationStatus } from "@/hooks/useSuperAdmin";
import { apiErrorMessage } from "@/lib/api";
import type { OrganizationAddress } from "@/types";
import { OwnerPasswordResetModal } from "@/components/OwnerPasswordResetModal";

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

function addressLines(address: OrganizationAddress | null): string[] {
  if (!address) return [];
  return [
    address.attention,
    address.line1,
    address.line2,
    [address.city, address.state, address.postal_code].filter(Boolean).join(", "),
    address.country,
    address.phone,
  ].filter((line): line is string => Boolean(line));
}

export default function OrganizationViewPage() {
  const params = useParams<{ id: string }>();
  const organizationId = Number(params.id);
  const { data: organization, isLoading, isError } = useOrganization(organizationId);
  const setStatus = useSetOrganizationStatus();
  const router = useRouter();
  const { message } = App.useApp();
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="flex min-h-80 items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }
  if (isError || !organization) {
    return <Result status="404" title="Organization not found" />;
  }

  const registeredAddress = addressLines(organization.address);
  const owner = organization.members.find((member) => member.is_owner);

  const changeStatus = async () => {
    const enabling = !organization.is_active;
    try {
      await setStatus.mutateAsync({ id: organization.id, isActive: enabling });
      message.success(`Organization ${enabling ? "enabled" : "disabled"}`);
    } catch (error) {
      message.error(apiErrorMessage(error, "Could not update organization access"));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div className="flex items-start gap-3">
          <Button
            type="text"
            icon={<ArrowLeft size={19} />}
            onClick={() => router.push("/organizations")}
            aria-label="Back to organizations"
          />
          <Avatar
            shape="square"
            size={56}
            src={organization.logo_url || undefined}
            icon={<Building2 size={26} />}
            className="!bg-teal-50 !text-teal-700"
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
            <Typography.Text type="secondary">
              {organization.slug} · Organization #{organization.id}
            </Typography.Text>
          </div>
        </div>
        <Space wrap>
          <Button
            danger={organization.is_active}
            icon={organization.is_active ? <Ban size={17} /> : <CheckCircle2 size={17} />}
            loading={setStatus.isPending}
            onClick={() => void changeStatus()}
          >
            {organization.is_active ? "Disable access" : "Enable access"}
          </Button>
          <Button
            type="primary"
            icon={<Edit3 size={17} />}
            onClick={() => router.push(`/organizations/${organization.id}/edit`)}
          >
            Edit organization
          </Button>
        </Space>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card size="small" className="border-slate-200">
          <div className="text-sm text-slate-500">Members</div>
          <div className="mt-1 text-2xl font-semibold text-slate-900">
            {organization.member_count}
          </div>
        </Card>
        <Card size="small" className="border-slate-200">
          <div className="text-sm text-slate-500">Base currency</div>
          <div className="mt-1 text-2xl font-semibold text-slate-900">
            {organization.currency}
          </div>
        </Card>
        <Card size="small" className="border-slate-200">
          <div className="text-sm text-slate-500">FBR integration</div>
          <div className="mt-2">
            <Tag color={organization.fbr_enabled ? "green" : "default"}>
              {organization.fbr_enabled ? "Enabled" : "Disabled"}
            </Tag>
          </div>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <div className="grid content-start gap-6">
          <Card
            title={
              <Space>
                <Building2 size={18} />
                Organization profile
              </Space>
            }
            className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]"
          >
            <Descriptions column={{ xs: 1, sm: 2, lg: 3 }} layout="vertical">
              <Descriptions.Item label="Organization name">{organization.name}</Descriptions.Item>
              <Descriptions.Item label="Industry">{organization.industry || "—"}</Descriptions.Item>
              <Descriptions.Item label="Country code">{organization.country}</Descriptions.Item>
              <Descriptions.Item label="NTN">{organization.ntn || "—"}</Descriptions.Item>
              <Descriptions.Item label="STRN">{organization.strn || "—"}</Descriptions.Item>
              <Descriptions.Item label="CNIC">{organization.cnic || "—"}</Descriptions.Item>
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

          <Card
            title={
              <Space>
                <Users size={18} />
                Organization members
              </Space>
            }
            extra={
              owner ? (
                <Button
                  size="small"
                  icon={<KeyRound size={15} />}
                  onClick={() => setPasswordModalOpen(true)}
                >
                  Reset owner password
                </Button>
              ) : null
            }
            className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]"
          >
            <Table
              rowKey="membership_id"
              pagination={false}
              dataSource={organization.members}
              locale={{ emptyText: "No members found" }}
              columns={[
                {
                  title: "Member",
                  key: "member",
                  render: (_, member) => (
                    <div>
                      <div className="flex items-center gap-2 font-medium text-slate-900">
                        {member.full_name || "Unnamed member"}
                        {member.is_owner && <Tag color="cyan">Owner</Tag>}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">{member.email}</div>
                    </div>
                  ),
                },
                {
                  title: "Role",
                  dataIndex: "role_name",
                  render: (role: string) => <span className="capitalize">{role}</span>,
                },
                {
                  title: "Status",
                  dataIndex: "is_active",
                  render: (active: boolean) => (
                    <Tag color={active ? "green" : "default"}>{active ? "Active" : "Inactive"}</Tag>
                  ),
                },
              ]}
            />
          </Card>
        </div>

        <div className="grid content-start gap-6">
          <Card
            title={
              <Space>
                <MapPin size={18} />
                Registered address
              </Space>
            }
            className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]"
          >
            {registeredAddress.length ? (
              <div className="space-y-1 text-sm leading-relaxed text-slate-700">
                {registeredAddress.map((line, index) => (
                  <div key={`${index}-${line}`}>{line}</div>
                ))}
              </div>
            ) : (
              <Typography.Text type="secondary">No registered address</Typography.Text>
            )}
          </Card>

          <Card
            title={
              <Space>
                <FileCheck2 size={18} />
                FBR compliance
              </Space>
            }
            extra={
              <Button
                size="small"
                icon={<PlayCircle size={15} />}
                onClick={() => router.push(`/organizations/${organization.id}/fbr/sandbox-tests`)}
              >
                Sandbox tests
              </Button>
            }
            className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]"
          >
            <Descriptions column={1} size="small">
              <Descriptions.Item label="Status">
                <Tag color={organization.fbr_enabled ? "green" : "default"}>
                  {organization.fbr_enabled ? "Enabled" : "Disabled"}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Environment">
                <span className="capitalize">{organization.fbr_environment}</span>
              </Descriptions.Item>
              <Descriptions.Item label="Province">
                {organization.fbr_province || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Sandbox token">
                {organization.fbr_sandbox_configured ? "Configured" : "Not configured"}
              </Descriptions.Item>
              <Descriptions.Item label="Production token">
                {organization.fbr_production_configured ? "Configured" : "Not configured"}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]">
            <div className="flex items-start gap-3">
              <div className="rounded-xl bg-teal-50 p-3 text-teal-700">
                {organization.is_active ? <ShieldCheck size={20} /> : <Ban size={20} />}
              </div>
              <div>
                <div className="font-medium text-slate-900">Platform access</div>
                <div className="mt-1 text-sm text-slate-500">
                  {organization.is_active
                    ? "Members can access this organization."
                    : "Member access is currently blocked."}
                </div>
                <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                  <CalendarDays size={14} /> Created organization record
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {owner && (
        <OwnerPasswordResetModal
          organizationId={organization.id}
          organizationName={organization.name}
          ownerEmail={owner.email}
          open={passwordModalOpen}
          onClose={() => setPasswordModalOpen(false)}
        />
      )}
    </div>
  );
}
