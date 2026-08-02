"use client";

import { useState } from "react";
import type { TableColumnsType } from "antd";
import { App, Button, Card, Input, Space, Switch, Table, Tag, Typography } from "antd";
import { Edit3, Eye, Plus, Search } from "lucide-react";
import { useRouter } from "next/navigation";

import { useOrganizations, useSetOrganizationStatus } from "@/hooks/useSuperAdmin";
import { apiErrorMessage } from "@/lib/api";
import type { Organization } from "@/types";

export default function OrganizationsPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const { data, isLoading } = useOrganizations(search, page);
  const setStatus = useSetOrganizationStatus();
  const { message } = App.useApp();
  const router = useRouter();

  const changeStatus = async (organization: Organization, isActive: boolean) => {
    try {
      await setStatus.mutateAsync({ id: organization.id, isActive });
      message.success(isActive ? "Organization activated" : "Organization deactivated");
    } catch (error) {
      message.error(apiErrorMessage(error, "Could not update organization"));
    }
  };

  const columns: TableColumnsType<Organization> = [
    {
      title: "Organization",
      dataIndex: "name",
      render: (_, row) => (
        <button
          type="button"
          onClick={() => router.push(`/organizations/${row.id}`)}
          className="cursor-pointer text-left"
        >
          <div className="font-medium text-slate-900 hover:text-teal-700">{row.name}</div>
          <div className="text-xs text-slate-500">{row.slug}</div>
        </button>
      ),
    },
    {
      title: "Owner",
      dataIndex: "owner_email",
      render: (_, row) => (
        <div>
          <div>{row.owner_name || "—"}</div>
          <div className="text-xs text-slate-500">{row.owner_email}</div>
        </div>
      ),
    },
    { title: "Members", dataIndex: "member_count", width: 100 },
    {
      title: "Region",
      key: "region",
      width: 130,
      render: (_, row) => `${row.country} · ${row.currency}`,
    },
    {
      title: "Status",
      dataIndex: "is_active",
      width: 110,
      render: (active: boolean) => (
        <Tag color={active ? "green" : "default"}>{active ? "Active" : "Inactive"}</Tag>
      ),
    },
    {
      title: "Enabled",
      key: "enabled",
      width: 100,
      render: (_, row) => (
        <Switch
          checked={row.is_active}
          loading={setStatus.isPending && setStatus.variables?.id === row.id}
          onChange={(checked) => void changeStatus(row, checked)}
          aria-label={`${row.is_active ? "Deactivate" : "Activate"} ${row.name}`}
        />
      ),
    },
    {
      title: "Actions",
      key: "actions",
      width: 130,
      fixed: "right",
      render: (_, row) => (
        <Space size={4}>
          <Button
            type="text"
            icon={<Eye size={16} />}
            onClick={() => router.push(`/organizations/${row.id}`)}
            aria-label={`View ${row.name}`}
          />
          <Button
            type="text"
            icon={<Edit3 size={16} />}
            onClick={() => router.push(`/organizations/${row.id}/edit`)}
            aria-label={`Edit ${row.name}`}
          />
        </Space>
      ),
    },
  ];

  return (
    <div className="w-full">
      <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <Typography.Title level={2} className="!mb-1 !text-3xl">
            Organizations
          </Typography.Title>
          <Typography.Text type="secondary">
            Onboard and manage customer organizations.
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

      <Card
        className="w-full border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]"
        styles={{ body: { padding: 0 } }}
      >
        <div className="border-b border-slate-100 p-4">
          <Input.Search
            allowClear
            prefix={<Search size={16} className="text-slate-400" />}
            placeholder="Search organizations"
            className="max-w-sm"
            onSearch={(value) => {
              setSearch(value.trim());
              setPage(1);
            }}
          />
        </div>
        <Table<Organization>
          rowKey="id"
          columns={columns}
          dataSource={data?.items ?? []}
          loading={isLoading}
          scroll={{ x: 1050 }}
          pagination={{
            current: page,
            pageSize: 20,
            total: data?.total ?? 0,
            showSizeChanger: false,
            onChange: setPage,
          }}
        />
      </Card>
    </div>
  );
}
