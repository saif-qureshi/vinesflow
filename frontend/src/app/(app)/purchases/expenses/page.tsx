"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import type { ColumnsType } from "antd/es/table";

import { Button, DataTable, PageHeader, Select, Tag, Typography } from "@/components/ui";
import { useCurrency } from "@/hooks/useCurrency";
import { useExpenseList, type ExpenseFilters } from "@/hooks/useExpenses";
import { useCan } from "@/hooks/useSession";
import { formatDate } from "@/lib/format";
import type { ExpenseStatus, ExpenseSummary } from "@/types";

const STATUS_META: Record<ExpenseStatus, { color: string; label: string }> = {
  draft: { color: "gold", label: "Draft" },
  submitted: { color: "green", label: "Submitted" },
  cancelled: { color: "red", label: "Cancelled" },
};

const STATUS_OPTIONS = [
  { value: "draft", label: "Draft" },
  { value: "submitted", label: "Submitted" },
  { value: "cancelled", label: "Cancelled" },
];

export default function ExpensesPage() {
  const router = useRouter();
  const can = useCan();
  const { money } = useCurrency();
  const [filters, setFilters] = useState<ExpenseFilters>({});
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useExpenseList(filters);
  const items = data?.pages.flatMap((p) => p.items) ?? [];
  const dash = <span className="text-gray-400">—</span>;

  const columns: ColumnsType<ExpenseSummary> = [
    {
      title: "Expense",
      key: "number",
      render: (_, e) => (
        <div>
          <div className="font-medium">{e.number}</div>
          <Typography.Text type="secondary" className="text-xs">
            {formatDate(e.expense_date)}
          </Typography.Text>
        </div>
      ),
    },
    { title: "Vendor", key: "vendor", render: (_, e) => e.vendor_name ?? dash },
    { title: "Reference", key: "ref", render: (_, e) => e.reference_no ?? dash },
    {
      title: "Status",
      key: "status",
      render: (_, e) => <Tag color={STATUS_META[e.status].color}>{STATUS_META[e.status].label}</Tag>,
    },
    {
      title: "Total",
      key: "total",
      align: "right",
      render: (_, e) => <span className="tabular-nums font-medium">{money(Number(e.total))}</span>,
    },
  ];

  const toolbar = (
    <Select
      value={filters.status ?? undefined}
      onChange={(status) => setFilters((f) => ({ ...f, status: status ?? null }))}
      allowClear
      placeholder="All statuses"
      options={STATUS_OPTIONS}
      className="!w-44"
    />
  );

  return (
    <div className="space-y-4">
      <PageHeader
        title="Expenses"
        description="Record out-of-pocket and paid business expenses."
        actions={
          can("expenses:create") && (
            <Button
              type="primary"
              icon={<Plus size={16} />}
              onClick={() => router.push("/purchases/expenses/new")}
            >
              New Expense
            </Button>
          )
        }
      />

      <DataTable<ExpenseSummary>
        loading={isLoading}
        columns={columns}
        dataSource={items}
        searchable
        searchPlaceholder="Search by expense number, vendor, or reference"
        onSearch={(search) => setFilters((f) => ({ ...f, search }))}
        toolbar={toolbar}
        onRowClick={(e) => router.push(`/purchases/expenses/${e.id}`)}
        hasMore={hasNextPage}
        onLoadMore={() => fetchNextPage()}
        loadingMore={isFetchingNextPage}
      />
    </div>
  );
}
