"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, MoreHorizontal, Pencil, Plus, Trash2 } from "lucide-react";
import type { ColumnsType } from "antd/es/table";
import type { MenuProps } from "antd";

import { App, Avatar, Button, DataTable, Dropdown, PageHeader, Tag, Typography } from "@/components/ui";
import { FilterDropdown } from "@/components/ui/FilterDropdown";
import { useCan } from "@/hooks/useSession";
import { useDeleteParty, useParties, type PartyFilters } from "@/hooks/useParties";
import { apiErrorMessage } from "@/lib/api";
import type { Party, PartyRole } from "@/types";

export function PartyList() {
  const router = useRouter();
  const { message, modal } = App.useApp();
  const can = useCan();
  const del = useDeleteParty();
  const [filters, setFilters] = useState<PartyFilters>({});
  const activeRole = filters.role ?? undefined;
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage } = useParties(activeRole, filters);

  const parties = data?.pages.flatMap((p) => p.items) ?? [];
  const patch = (f: Partial<PartyFilters>) => setFilters((prev) => ({ ...prev, ...f }));
  const dash = <span className="text-gray-400">—</span>;

  const confirmDelete = (p: Party) => {
    modal.confirm({
      title: "Delete this party?",
      content: `"${p.name}" will be permanently deleted.`,
      okText: "Delete",
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await del.mutateAsync(p.id);
          message.success("Party deleted");
        } catch (err) {
          message.error(apiErrorMessage(err));
          throw err;
        }
      },
    });
  };

  const rowMenu = (p: Party): MenuProps["items"] => [
    { key: "view", icon: <Eye size={14} />, label: "View", onClick: () => router.push(`/parties/${p.id}`) },
    ...(can("parties:update")
      ? [{ key: "edit", icon: <Pencil size={14} />, label: "Edit", onClick: () => router.push(`/parties/${p.id}/edit`) }]
      : []),
    ...(can("parties:delete")
      ? [
          { type: "divider" as const },
          { key: "delete", icon: <Trash2 size={14} />, label: "Delete", danger: true, onClick: () => confirmDelete(p) },
        ]
      : []),
  ];

  const columns: ColumnsType<Party> = [
    {
      title: "Name",
      key: "name",
      render: (_, p) => (
        <div className="flex items-center gap-3">
          <Avatar shape="square" size={36} src={p.avatar_url ?? undefined} className="shrink-0 !bg-gray-100 !text-gray-500">
            {p.name.charAt(0).toUpperCase()}
          </Avatar>
          <div>
            <div className="font-medium">{p.name}</div>
            {p.company_name && p.company_name !== p.name && (
              <Typography.Text type="secondary" className="text-xs">
                {p.company_name}
              </Typography.Text>
            )}
          </div>
        </div>
      ),
    },
    { title: "Email", key: "email", render: (_, p) => p.email || dash },
    { title: "Phone", key: "phone", render: (_, p) => p.work_phone || p.mobile || dash },
    {
      title: "Roles",
      key: "roles",
      render: (_, p) => (
        <div className="flex gap-1">
          {p.is_customer && <Tag color="blue">Customer</Tag>}
          {p.is_vendor && <Tag color="purple">Vendor</Tag>}
        </div>
      ),
    },
    {
      title: "Status",
      key: "status",
      render: (_, p) => (p.is_active ? <Tag color="green">Active</Tag> : <Tag>Inactive</Tag>),
    },
    {
      title: "",
      key: "actions",
      width: 56,
      align: "right",
      render: (_, p) => (
        <div onClick={(e) => e.stopPropagation()}>
          <Dropdown trigger={["click"]} menu={{ items: rowMenu(p) }} placement="bottomRight">
            <Button type="text" icon={<MoreHorizontal size={16} />} />
          </Dropdown>
        </div>
      ),
    },
  ];

  const toolbar = (
    <FilterDropdown
      groups={[
        {
          key: "role",
          label: "Role",
          value: filters.role ?? null,
          options: [
            { value: "customer", label: "Customer" },
            { value: "vendor", label: "Vendor" },
          ],
          onChange: (v) => patch({ role: (v as PartyRole | null) ?? null }),
        },
        {
          key: "type",
          label: "Type",
          value: filters.type ?? null,
          options: [
            { value: "business", label: "Business" },
            { value: "individual", label: "Individual" },
          ],
          onChange: (v) => patch({ type: (v as "business" | "individual" | null) ?? null }),
        },
        {
          key: "status",
          label: "Status",
          value: filters.is_active == null ? null : filters.is_active ? "active" : "inactive",
          options: [
            { value: "active", label: "Active" },
            { value: "inactive", label: "Inactive" },
          ],
          onChange: (v) => patch({ is_active: v == null ? null : v === "active" }),
        },
      ]}
    />
  );

  return (
    <div className="space-y-4">
      <PageHeader
        title="Parties"
        description="People and businesses you buy from or sell to"
        actions={
          can("parties:create") && (
            <Button type="primary" icon={<Plus size={16} />} onClick={() => router.push("/parties/new")}>
              New Party
            </Button>
          )
        }
      />

      <DataTable<Party>
        loading={isLoading}
        columns={columns}
        dataSource={parties}
        searchable
        searchPlaceholder="Search parties"
        onSearch={(search) => patch({ search })}
        toolbar={toolbar}
        onRowClick={(p) => router.push(`/parties/${p.id}`)}
        hasMore={hasNextPage}
        onLoadMore={() => fetchNextPage()}
        loadingMore={isFetchingNextPage}
      />
    </div>
  );
}
