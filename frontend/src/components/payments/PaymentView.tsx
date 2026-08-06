"use client";

import { useRouter } from "next/navigation";

import { errorState, loadingState, notFoundState } from "@/components/ui/QueryFallback";
import { Descriptions, Table } from "antd";
import type { ColumnsType } from "antd/es/table";
import { ArrowLeft, Ban, CheckCircle2, Trash2 } from "lucide-react";

import { App, Button, Card, Popconfirm, Tag, Typography } from "@/components/ui";
import { useCurrency } from "@/hooks/useCurrency";
import {
  useCancelPayment,
  useDeletePayment,
  usePayment,
  useSubmitPayment,
} from "@/hooks/usePayments";
import { useCan } from "@/hooks/useSession";
import { apiErrorMessage } from "@/lib/api";
import type { PaymentKindConfig } from "@/lib/paymentKinds";
import { formatDate } from "@/lib/format";
import type { PaymentAllocation } from "@/types";
import { METHOD_LABEL, PAYMENT_STATUS_META } from "./status";

export function PaymentView({ config, id }: { config: PaymentKindConfig; id: number }) {
  const router = useRouter();
  const { message } = App.useApp();
  const { money } = useCurrency();
  const can = useCan();
  const { data: pay, isLoading, error } = usePayment(config.apiPath, id);
  const submit = useSubmitPayment(config.apiPath);
  const cancel = useCancelPayment(config.apiPath);
  const del = useDeletePayment(config.apiPath);

  if (error) return errorState(error);
  if (isLoading) return loadingState();
  if (!pay) return notFoundState();

  const dash = <span className="text-gray-400">—</span>;
  const meta = PAYMENT_STATUS_META[pay.status];

  const run = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      message.success(ok);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const columns: ColumnsType<PaymentAllocation> = [
    { title: "Document", key: "doc", render: (_, a) => a.document_number },
    {
      title: "Applied",
      key: "amount",
      align: "right",
      render: (_, a) => <span className="tabular-nums font-medium">{money(Number(a.amount))}</span>,
    },
  ];

  return (
    <div className="flex flex-col gap-6 pb-10">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-2">
          <Button
            type="text"
            icon={<ArrowLeft size={18} />}
            onClick={() => router.push(config.basePath)}
            className="!mt-0.5"
          />
          <div>
            <Typography.Title level={3} className="!mb-1">
              {pay.number}
            </Typography.Title>
            <div className="flex flex-wrap items-center gap-2">
              <Tag color={meta?.color}>{meta?.label ?? pay.status}</Tag>
              <Typography.Text type="secondary">{pay.party_name}</Typography.Text>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {pay.status === "draft" && can("payments:update") && (
            <Button
              type="primary"
              icon={<CheckCircle2 size={16} />}
              loading={submit.isPending}
              onClick={() => run(() => submit.mutateAsync(pay.id), "Payment submitted")}
            >
              Submit
            </Button>
          )}
          {pay.status === "draft" && can("payments:delete") && (
            <Popconfirm
              title="Delete this draft?"
              okText="Delete"
              okButtonProps={{ danger: true, loading: del.isPending }}
              onConfirm={async () => {
                await run(() => del.mutateAsync(pay.id), "Payment deleted");
                router.push(config.basePath);
              }}
            >
              <Button danger icon={<Trash2 size={16} />} />
            </Popconfirm>
          )}
          {pay.status === "submitted" && can("payments:update") && (
            <Popconfirm
              title="Cancel this payment?"
              description="Settlements will be reversed."
              okText="Cancel payment"
              okButtonProps={{ danger: true, loading: cancel.isPending }}
              onConfirm={() => run(() => cancel.mutateAsync(pay.id), "Payment cancelled")}
            >
              <Button danger icon={<Ban size={16} />}>
                Cancel
              </Button>
            </Popconfirm>
          )}
        </div>
      </div>

      <Card className="border-gray-100">
        <Descriptions column={{ xs: 1, md: 4 }} colon={false} size="small">
          <Descriptions.Item label={config.labels.party}>{pay.party_name ?? dash}</Descriptions.Item>
          <Descriptions.Item label="Date">{formatDate(pay.document_date)}</Descriptions.Item>
          <Descriptions.Item label="Method">{METHOD_LABEL[pay.method] ?? pay.method}</Descriptions.Item>
          <Descriptions.Item label="Reference">{pay.reference || dash}</Descriptions.Item>
          <Descriptions.Item label="Amount">
            <span className="tabular-nums font-semibold">{money(Number(pay.amount))}</span>
          </Descriptions.Item>
          <Descriptions.Item label="Applied">{money(Number(pay.allocated_amount))}</Descriptions.Item>
          <Descriptions.Item label="Unapplied">{money(Number(pay.unapplied_amount))}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="Applied to" className="border-gray-100">
        <Table<PaymentAllocation>
          size="small"
          rowKey="id"
          columns={columns}
          dataSource={pay.allocations}
          pagination={false}
          locale={{ emptyText: "Unapplied — held as a credit" }}
        />
      </Card>

      {pay.notes && (
        <Card className="border-gray-100">
          <div className="text-xs text-gray-400">Notes</div>
          <div className="mt-1 whitespace-pre-wrap text-sm text-gray-600">{pay.notes}</div>
        </Card>
      )}
    </div>
  );
}
