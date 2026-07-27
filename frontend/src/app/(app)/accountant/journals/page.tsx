"use client";

import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import type { ColumnsType } from "antd/es/table";

import { Button, DataTable, PageHeader, Tag } from "@/components/ui";
import { useVouchers } from "@/hooks/useAccounting";
import { useCurrency } from "@/hooks/useCurrency";
import type { VoucherStatus, VoucherSummary } from "@/types";

const STATUS_COLOR: Record<VoucherStatus, string> = {
  posted: "green",
  reversed: "gold",
  cancelled: "red",
  draft: "blue",
};

export default function JournalsPage() {
  const router = useRouter();
  const { money } = useCurrency();
  const vouchers = useVouchers();

  const columns: ColumnsType<VoucherSummary> = [
    {
      title: "Number",
      dataIndex: "number",
      render: (v) => <span className="font-mono text-slate-500">{v}</span>,
    },
    { title: "Date", dataIndex: "posting_date", width: 120 },
    {
      title: "Type",
      dataIndex: "voucher_type",
      render: (t: string) => <Tag className="capitalize">{t.replace(/_/g, " ")}</Tag>,
    },
    { title: "Description", dataIndex: "description", render: (d) => d || "—" },
    {
      title: "Amount",
      dataIndex: "total_debit",
      align: "right",
      render: (v) => <span className="tabular-nums">{money(Number(v))}</span>,
    },
    {
      title: "Status",
      dataIndex: "status",
      width: 110,
      render: (s: VoucherStatus) => <Tag color={STATUS_COLOR[s]}>{s}</Tag>,
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Journals"
        description="Every posted voucher — automatic and manual"
        actions={
          <Button
            type="primary"
            icon={<Plus size={16} />}
            onClick={() => router.push("/accountant/journals/new")}
          >
            New journal
          </Button>
        }
      />
      <DataTable<VoucherSummary>
        rowKey="id"
        columns={columns}
        dataSource={vouchers.data ?? []}
        loading={vouchers.isLoading}
        onRow={(r) => ({
          onClick: () => router.push(`/accountant/journals/${r.id}`),
          className: "cursor-pointer",
        })}
      />
    </div>
  );
}
