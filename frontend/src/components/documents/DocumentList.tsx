"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Select } from "antd";
import type { MenuProps } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Download, Eye, MoreHorizontal, Pencil, Plus, Trash2 } from "lucide-react";

import { App, Button, DataTable, Dropdown, PageHeader, Tag, Typography } from "@/components/ui";
import { useCurrency } from "@/hooks/useCurrency";
import { useDeleteDocument, useDocumentList, type DocumentFilters } from "@/hooks/useDocuments";
import { useCan } from "@/hooks/useSession";
import { apiErrorMessage } from "@/lib/api";
import { downloadDocumentPdf } from "@/lib/documentPdf";
import type { DocumentKindConfig } from "@/lib/documentKinds";
import { formatDate } from "@/lib/format";
import type { DocumentSummary } from "@/types";
import { documentFilterOptions, lifecycleMeta, PAYMENT_META } from "./status";

export function DocumentList({ config }: { config: DocumentKindConfig }) {
  const router = useRouter();
  const can = useCan();
  const { money } = useCurrency();
  const { message } = App.useApp();
  const [filters, setFilters] = useState<DocumentFilters>({});
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage } = useDocumentList(
    config.apiPath,
    filters,
  );
  const del = useDeleteDocument(config.apiPath);

  const items = data?.pages.flatMap((p) => p.items) ?? [];
  const patch = (f: Partial<DocumentFilters>) => setFilters((prev) => ({ ...prev, ...f }));
  const dash = <span className="text-gray-400">—</span>;

  const applyBadgeFilter = (value?: string) => {
    if (!value) return patch({ status: null, payment_status: null });
    if (["draft", "sent", "closed", "void"].includes(value))
      return patch({ status: value as DocumentFilters["status"], payment_status: null });
    if (value === "unpaid") return patch({ status: "sent", payment_status: "unpaid" });
    return patch({ status: "sent", payment_status: value });
  };
  const badgeFilter = filters.payment_status ?? filters.status ?? undefined;

  const remove = async (id: number) => {
    try {
      await del.mutateAsync(id);
      message.success(`${config.labels.singular} deleted`);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const rowMenu = (doc: DocumentSummary): MenuProps["items"] => [
    {
      key: "view",
      icon: <Eye size={14} />,
      label: "View",
      onClick: () => router.push(`${config.basePath}/${doc.id}`),
    },
    {
      key: "download",
      icon: <Download size={14} />,
      label: "Download",
      onClick: async () => {
        try {
          await downloadDocumentPdf(config.apiPath, doc.id, doc.number);
        } catch (err) {
          message.error(apiErrorMessage(err));
        }
      },
    },
    ...(doc.status === "draft" && can(`${config.permission}:update`)
      ? [
          {
            key: "edit",
            icon: <Pencil size={14} />,
            label: "Edit",
            onClick: () => router.push(`${config.basePath}/${doc.id}/edit`),
          },
        ]
      : []),
    ...(doc.status === "draft" && can(`${config.permission}:delete`)
      ? [
          {
            key: "delete",
            icon: <Trash2 size={14} />,
            label: "Delete",
            danger: true,
            onClick: () => remove(doc.id),
          },
        ]
      : []),
  ];

  const columns: ColumnsType<DocumentSummary> = [
    {
      title: config.labels.singular,
      key: "number",
      render: (_, doc) => (
        <div>
          <div className="font-medium">{doc.number}</div>
          <Typography.Text type="secondary" className="text-xs">
            {formatDate(doc.issue_date)}
          </Typography.Text>
        </div>
      ),
    },
    { title: config.labels.party, key: "party", render: (_, doc) => doc.party?.name ?? dash },
    {
      title: "Due date",
      key: "due",
      render: (_, doc) => (doc.due_date ? formatDate(doc.due_date) : dash),
    },
    {
      title: "Status",
      key: "status",
      render: (_, doc) => {
        const life = lifecycleMeta(doc.status, config);
        return (
          <div className="flex flex-wrap gap-1">
            <Tag color={life.color}>{life.label}</Tag>
            {config.tracksPayment && doc.status === "sent" && (
              <Tag color={PAYMENT_META[doc.payment_status].color}>
                {PAYMENT_META[doc.payment_status].label}
              </Tag>
            )}
          </div>
        );
      },
    },
    {
      title: "Total",
      key: "total",
      align: "right",
      render: (_, doc) => <span className="tabular-nums">{money(Number(doc.total))}</span>,
    },
    ...(config.tracksPayment
      ? [
          {
            title: "Balance due",
            key: "balance",
            align: "right" as const,
            render: (_: unknown, doc: DocumentSummary) => (
              <span className="tabular-nums font-medium">{money(Number(doc.balance_due))}</span>
            ),
          },
        ]
      : []),
    {
      title: "",
      key: "actions",
      width: 56,
      align: "right",
      render: (_, doc) => (
        <div onClick={(e) => e.stopPropagation()}>
          <Dropdown trigger={["click"]} menu={{ items: rowMenu(doc) }} placement="bottomRight">
            <Button type="text" icon={<MoreHorizontal size={16} />} />
          </Dropdown>
        </div>
      ),
    },
  ];

  const toolbar = (
    <Select
      value={badgeFilter}
      onChange={applyBadgeFilter}
      allowClear
      placeholder="All statuses"
      options={documentFilterOptions(config)}
      className="!w-44"
    />
  );

  return (
    <div className="space-y-4">
      <PageHeader
        title={config.labels.listTitle}
        description={config.labels.listDescription}
        actions={
          can(`${config.permission}:create`) && (
            <Button
              type="primary"
              icon={<Plus size={16} />}
              onClick={() => router.push(`${config.basePath}/new`)}
            >
              {config.labels.newAction}
            </Button>
          )
        }
      />

      <DataTable<DocumentSummary>
        loading={isLoading}
        columns={columns}
        dataSource={items}
        searchable
        searchPlaceholder={`Search by ${config.labels.singular.toLowerCase()} number or reference`}
        onSearch={(search) => patch({ search })}
        toolbar={toolbar}
        onRowClick={(doc) => router.push(`${config.basePath}/${doc.id}`)}
        hasMore={hasNextPage}
        onLoadMore={() => fetchNextPage()}
        loadingMore={isFetchingNextPage}
      />
    </div>
  );
}
