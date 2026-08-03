"use client";

import { Plus, Trash2 } from "lucide-react";
import { DatePicker, InputNumber } from "antd";
import type { Dayjs } from "dayjs";

import { Button, Card, Form, Input, Select, TextArea } from "@/components/ui";
import { useAccounts } from "@/hooks/useAccounting";
import { useCurrency } from "@/hooks/useCurrency";
import { useParties } from "@/hooks/useParties";

const GRID_COLUMNS = "md:grid-cols-[1.6fr_1.4fr_150px_40px]";

export interface ExpenseLineForm {
  account_id?: number;
  description?: string;
  amount?: number;
}

export interface ExpenseFormValues {
  expense_date: Dayjs;
  paid_through_account_id?: number;
  vendor_id?: number;
  reference_no?: string;
  tax_amount?: number;
  notes?: string;
  lines: ExpenseLineForm[];
}

export function ExpenseForm({
  initialValues,
  submitLabel,
  pending,
  onSubmit,
  onCancel,
}: {
  initialValues: ExpenseFormValues;
  submitLabel: string;
  pending: boolean;
  onSubmit: (values: ExpenseFormValues) => void;
  onCancel: () => void;
}) {
  const { money } = useCurrency();
  const [form] = Form.useForm<ExpenseFormValues>();
  const accounts = useAccounts();
  const vendors = useParties("vendor");

  const postable = (accounts.data ?? []).filter((a) => a.is_postable);
  const categoryOptions = postable
    .filter((a) => a.account_type === "expense")
    .map((a) => ({ value: a.id, label: `${a.code} — ${a.name}` }));
  const paidThroughOptions = postable
    .filter((a) => a.account_type === "asset" || a.account_type === "liability")
    .map((a) => ({ value: a.id, label: `${a.code} — ${a.name}` }));
  const vendorOptions = (vendors.data?.pages.flatMap((p) => p.items) ?? []).map((v) => ({
    value: v.id,
    label: v.name,
  }));

  const lines = (Form.useWatch("lines", form) ?? []) as ExpenseLineForm[];
  const taxAmount = Number(Form.useWatch("tax_amount", form) || 0);
  const subtotal = lines.reduce((s, l) => s + Number(l?.amount || 0), 0);
  const total = subtotal + taxAmount;

  return (
    <Card>
      <Form form={form} layout="vertical" onFinish={onSubmit} initialValues={initialValues}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Form.Item name="expense_date" label="Date" rules={[{ required: true }]}>
            <DatePicker className="!w-full" format="DD MMM YYYY" allowClear={false} />
          </Form.Item>
          <Form.Item
            name="paid_through_account_id"
            label="Paid through"
            rules={[{ required: true, message: "Select a paid-through account" }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="Cash / Bank"
              loading={accounts.isLoading}
              options={paidThroughOptions}
            />
          </Form.Item>
          <Form.Item name="vendor_id" label="Vendor">
            <Select
              showSearch
              allowClear
              optionFilterProp="label"
              placeholder="Optional"
              loading={vendors.isLoading}
              options={vendorOptions}
            />
          </Form.Item>
        </div>

        <div className="mb-2 text-xs font-medium text-gray-400">Categories</div>
        <Form.List name="lines">
          {(fields, { add, remove }) => (
            <div className="space-y-2">
              <div className={`hidden ${GRID_COLUMNS} px-1 text-xs text-gray-400 md:grid`}>
                <span>Category account</span>
                <span>Description</span>
                <span className="text-right">Amount</span>
                <span />
              </div>
              {fields.map(({ key, name, ...rest }) => (
                <div
                  key={key}
                  className={`grid grid-cols-1 gap-2 rounded-lg border border-gray-100 p-3 ${GRID_COLUMNS} md:rounded-none md:border-0 md:p-0`}
                >
                  <Form.Item
                    {...rest}
                    name={[name, "account_id"]}
                    rules={[{ required: true, message: "" }]}
                    className="!mb-0"
                  >
                    <Select
                      showSearch
                      optionFilterProp="label"
                      placeholder="Select category"
                      loading={accounts.isLoading}
                      options={categoryOptions}
                    />
                  </Form.Item>
                  <Form.Item {...rest} name={[name, "description"]} className="!mb-0">
                    <Input placeholder="Optional note" />
                  </Form.Item>
                  <Form.Item
                    {...rest}
                    name={[name, "amount"]}
                    rules={[{ required: true, message: "" }]}
                    className="!mb-0"
                  >
                    <InputNumber className="!w-full" min={0} placeholder="Amount" />
                  </Form.Item>
                  <Button
                    type="text"
                    danger
                    icon={<Trash2 size={15} />}
                    onClick={() => remove(name)}
                    disabled={fields.length <= 1}
                  />
                </div>
              ))}
              <Button type="dashed" icon={<Plus size={14} />} onClick={() => add({})} block>
                Add category
              </Button>
            </div>
          )}
        </Form.List>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Form.Item name="reference_no" label="Reference #">
            <Input placeholder="Optional" />
          </Form.Item>
          <Form.Item name="tax_amount" label="Input tax">
            <InputNumber className="!w-full" min={0} placeholder="0" />
          </Form.Item>
        </div>
        <Form.Item name="notes" label="Notes">
          <TextArea rows={2} maxLength={500} placeholder="What was this expense for?" />
        </Form.Item>

        <div className="mt-2 flex flex-wrap items-center justify-end gap-x-6 gap-y-2 rounded-lg bg-slate-50 p-3 text-sm text-gray-500">
          <span>
            Subtotal <b className="tabular-nums text-slate-800">{money(subtotal)}</b>
          </span>
          <span>
            Tax <b className="tabular-nums text-slate-800">{money(taxAmount)}</b>
          </span>
          <span>
            Total <b className="tabular-nums text-slate-900">{money(total)}</b>
          </span>
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <Button onClick={onCancel}>Cancel</Button>
          <Button type="primary" htmlType="submit" loading={pending} disabled={total <= 0}>
            {submitLabel}
          </Button>
        </div>
      </Form>
    </Card>
  );
}
