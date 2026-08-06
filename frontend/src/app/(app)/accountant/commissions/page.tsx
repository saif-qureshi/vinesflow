"use client";

import { useState } from "react";
import { DatePicker, InputNumber } from "antd";
import dayjs from "dayjs";
import { Plus } from "lucide-react";
import type { ColumnsType } from "antd/es/table";

import {
  App,
  Button,
  Card,
  DataTable,
  Form,
  FormModal,
  Input,
  PageHeader,
  Popconfirm,
  Select,
  StatCard,
  Tag,
} from "@/components/ui";
import { errorState } from "@/components/ui/QueryFallback";
import { useAccounts } from "@/hooks/useAccounting";
import {
  useCancelPayout,
  useCommissionBalances,
  useCommissionPayouts,
  useCreatePayout,
  useDeletePayout,
  useSubmitPayout,
} from "@/hooks/useCommissions";
import { useCurrency } from "@/hooks/useCurrency";
import { useSalespeople } from "@/hooks/useSalespeople";
import { useCan } from "@/hooks/useSession";
import { apiErrorMessage } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { CommissionBalance, CommissionPayout } from "@/types";

const STATUS_META: Record<string, { label: string; color?: string }> = {
  draft: { label: "Draft" },
  submitted: { label: "Paid", color: "green" },
  cancelled: { label: "Cancelled", color: "red" },
};

interface FormValues {
  salesperson_id: number;
  amount: number;
  paid_through_account_id: number;
  payout_date: dayjs.Dayjs;
  reference?: string;
}

export default function CommissionsPage() {
  const { message } = App.useApp();
  const { money } = useCurrency();
  const can = useCan();
  const balances = useCommissionBalances();
  const payouts = useCommissionPayouts();
  const salespeople = useSalespeople(true);
  const accounts = useAccounts();
  const create = useCreatePayout();
  const submit = useSubmitPayout();
  const cancel = useCancelPayout();
  const del = useDeletePayout();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm<FormValues>();

  const canPay = can("payments:create");
  const rows = balances.data ?? [];
  const total = (key: "earned" | "paid" | "outstanding") =>
    rows.reduce((sum, row) => sum + Number(row[key]), 0);

  const openCreate = () => {
    form.resetFields();
    form.setFieldsValue({ payout_date: dayjs() });
    setOpen(true);
  };

  const save = async (values: FormValues) => {
    try {
      const created = await create.mutateAsync({
        salesperson_id: values.salesperson_id,
        amount: values.amount,
        paid_through_account_id: values.paid_through_account_id,
        payout_date: values.payout_date.format("YYYY-MM-DD"),
        reference: values.reference || null,
      });
      await submit.mutateAsync(created.data.id);
      message.success("Commission paid");
      setOpen(false);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const act = async (fn: () => Promise<unknown>, done: string) => {
    try {
      await fn();
      message.success(done);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const balanceColumns: ColumnsType<CommissionBalance> = [
    {
      title: "Salesperson",
      key: "salesperson",
      render: (_, row) => <span className="font-medium">{row.salesperson.name}</span>,
    },
    {
      title: "Earned",
      key: "earned",
      align: "right",
      render: (_, row) => <span className="tabular-nums">{money(Number(row.earned))}</span>,
    },
    {
      title: "Paid",
      key: "paid",
      align: "right",
      render: (_, row) => <span className="tabular-nums">{money(Number(row.paid))}</span>,
    },
    {
      title: "Outstanding",
      key: "outstanding",
      align: "right",
      render: (_, row) => (
        <span className="tabular-nums font-medium">{money(Number(row.outstanding))}</span>
      ),
    },
  ];

  const payoutColumns: ColumnsType<CommissionPayout> = [
    { title: "Number", dataIndex: "number", key: "number" },
    {
      title: "Salesperson",
      key: "salesperson",
      render: (_, row) => row.salesperson.name,
    },
    {
      title: "Date",
      key: "payout_date",
      render: (_, row) => formatDate(row.payout_date),
    },
    {
      title: "Amount",
      key: "amount",
      align: "right",
      render: (_, row) => <span className="tabular-nums">{money(Number(row.amount))}</span>,
    },
    {
      title: "Status",
      key: "status",
      render: (_, row) => {
        const meta = STATUS_META[row.status] ?? { label: row.status };
        return <Tag color={meta.color}>{meta.label}</Tag>;
      },
    },
    {
      title: "Actions",
      key: "actions",
      align: "right",
      render: (_, row) =>
        can("payments:update") && (
          <div className="flex justify-end gap-1">
            {row.status === "draft" && (
              <Button
                size="small"
                type="text"
                onClick={() => act(() => submit.mutateAsync(row.id), "Commission paid")}
              >
                Pay
              </Button>
            )}
            {row.status === "submitted" && (
              <Popconfirm
                title="Cancel this payout?"
                onConfirm={() => act(() => cancel.mutateAsync(row.id), "Payout cancelled")}
              >
                <Button size="small" type="text" danger>
                  Cancel
                </Button>
              </Popconfirm>
            )}
            {row.status === "draft" && (
              <Popconfirm
                title="Delete this payout?"
                onConfirm={() => act(() => del.mutateAsync(row.id), "Payout deleted")}
              >
                <Button size="small" type="text" danger>
                  Delete
                </Button>
              </Popconfirm>
            )}
          </div>
        ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Commissions"
        description="What each salesperson has earned, and what you have paid them"
        actions={
          canPay && (
            <Button type="primary" icon={<Plus size={16} />} onClick={openCreate}>
              Pay commission
            </Button>
          )
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard title="Earned" value={money(total("earned"))} />
        <StatCard title="Paid" value={money(total("paid"))} />
        <StatCard title="Outstanding" value={money(total("outstanding"))} />
      </div>

      {balances.error && errorState(balances.error)}
      <Card title="By salesperson" className="border-gray-100">
        <DataTable<CommissionBalance>
          rowKey={(row) => row.salesperson.id}
          columns={balanceColumns}
          dataSource={rows}
          loading={balances.isLoading}
        />
      </Card>

      <Card title="Payouts" className="border-gray-100">
        <DataTable<CommissionPayout>
          columns={payoutColumns}
          dataSource={payouts.data ?? []}
          loading={payouts.isLoading}
        />
      </Card>

      <FormModal
        title="Pay commission"
        open={open}
        form={form}
        onCancel={() => setOpen(false)}
        onSubmit={save}
        confirmLoading={create.isPending || submit.isPending}
      >
        <Form.Item name="salesperson_id" label="Salesperson" rules={[{ required: true }]}>
          <Select
            showSearch
            optionFilterProp="label"
            placeholder="Select salesperson"
            options={(salespeople.data ?? []).map((s) => ({ value: s.id, label: s.name }))}
          />
        </Form.Item>
        <Form.Item name="amount" label="Amount" rules={[{ required: true }]}>
          <InputNumber min={0} step={100} className="!w-full" />
        </Form.Item>
        <Form.Item
          name="paid_through_account_id"
          label="Paid through"
          rules={[{ required: true }]}
        >
          <Select
            showSearch
            optionFilterProp="label"
            placeholder="Select account"
            options={(accounts.data ?? [])
              .filter((a) => a.is_postable)
              .map((a) => ({ value: a.id, label: `${a.code} — ${a.name}` }))}
          />
        </Form.Item>
        <Form.Item name="payout_date" label="Date" rules={[{ required: true }]}>
          <DatePicker className="!w-full" format="DD MMM YYYY" />
        </Form.Item>
        <Form.Item name="reference" label="Reference">
          <Input placeholder="Optional" />
        </Form.Item>
      </FormModal>
    </div>
  );
}
