"use client";

import { useParams, useRouter } from "next/navigation";
import { useMemo } from "react";
import type { ColumnsType } from "antd/es/table";

import { App, Button, Card, DataTable, PageHeader, Popconfirm, Spin, Tag } from "@/components/ui";
import {
  useAccounts,
  useCancelVoucher,
  usePostVoucher,
  useReverseVoucher,
  useVoucher,
} from "@/hooks/useAccounting";
import { useCurrency } from "@/hooks/useCurrency";
import { apiErrorMessage } from "@/lib/api";
import type { VoucherLine } from "@/types";

const STATUS_COLOR: Record<string, string> = {
  draft: "blue",
  posted: "green",
  reversed: "gold",
  cancelled: "default",
};

export default function VoucherDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { message } = App.useApp();
  const { money } = useCurrency();
  const { data: voucher, isLoading } = useVoucher(Number(id));
  const accounts = useAccounts();
  const reverse = useReverseVoucher();
  const post = usePostVoucher();
  const cancel = useCancelVoucher();

  const nameOf = useMemo(() => {
    const map = new Map((accounts.data ?? []).map((a) => [a.id, `${a.code} — ${a.name}`]));
    return (accountId: number) => map.get(accountId) ?? `#${accountId}`;
  }, [accounts.data]);

  if (isLoading || !voucher) {
    return (
      <div className="flex justify-center p-12">
        <Spin />
      </div>
    );
  }

  const doReverse = async () => {
    try {
      const res = await reverse.mutateAsync(voucher.id);
      message.success(`Reversed — ${res.data.number}`);
      router.push("/accountant/journals");
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const doPost = async () => {
    try {
      await post.mutateAsync(voucher.id);
      message.success(`Posted ${voucher.number}`);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const doCancel = async () => {
    try {
      await cancel.mutateAsync(voucher.id);
      message.success("Draft cancelled");
      router.push("/accountant/journals");
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const columns: ColumnsType<VoucherLine> = [
    { title: "Account", dataIndex: "account_id", render: (a: number) => nameOf(a) },
    { title: "Description", dataIndex: "description", render: (d) => d || "—" },
    {
      title: "Debit",
      dataIndex: "debit",
      align: "right",
      render: (v) => (Number(v) ? <span className="tabular-nums">{money(Number(v))}</span> : "—"),
    },
    {
      title: "Credit",
      dataIndex: "credit",
      align: "right",
      render: (v) => (Number(v) ? <span className="tabular-nums">{money(Number(v))}</span> : "—"),
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title={voucher.number}
        description={voucher.description ?? undefined}
        onBack={() => router.push("/accountant/journals")}
        actions={
          <div className="flex items-center gap-2">
            <Tag color={STATUS_COLOR[voucher.status]}>{voucher.status}</Tag>
            {voucher.status === "draft" && (
              <>
                <Button onClick={() => router.push(`/accountant/journals/${voucher.id}/edit`)}>
                  Edit
                </Button>
                <Popconfirm
                  title="Cancel this draft?"
                  okText="Cancel draft"
                  okButtonProps={{ danger: true }}
                  onConfirm={doCancel}
                >
                  <Button danger loading={cancel.isPending}>
                    Cancel
                  </Button>
                </Popconfirm>
                <Button type="primary" loading={post.isPending} onClick={doPost}>
                  Post
                </Button>
              </>
            )}
            {voucher.status === "posted" && (
              <Popconfirm
                title="Reverse this voucher?"
                description="Posts a mirror-image entry and marks this one reversed."
                okText="Reverse"
                okButtonProps={{ danger: true }}
                onConfirm={doReverse}
              >
                <Button danger loading={reverse.isPending}>
                  Reverse
                </Button>
              </Popconfirm>
            )}
          </div>
        }
      />
      <Card>
        <div className="mb-4 flex gap-8 text-sm text-gray-500">
          <span>
            Date <b className="text-slate-800">{voucher.posting_date}</b>
          </span>
          <span>
            Total <b className="tabular-nums text-slate-800">{money(Number(voucher.total_debit))}</b>
          </span>
        </div>
        <DataTable<VoucherLine>
          rowKey="id"
          columns={columns}
          dataSource={voucher.lines}
          pagination={false}
        />
      </Card>
    </div>
  );
}
