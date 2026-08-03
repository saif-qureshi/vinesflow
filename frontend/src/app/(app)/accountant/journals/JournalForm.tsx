"use client";

import { Plus, Trash2 } from "lucide-react";
import { DatePicker, InputNumber } from "antd";
import type { Dayjs } from "dayjs";

import { Button, Card, Form, Input, Select, Tag } from "@/components/ui";
import { useAccounts } from "@/hooks/useAccounting";
import { useCurrency } from "@/hooks/useCurrency";

const GRID_COLUMNS = "md:grid-cols-[1.4fr_1fr_130px_130px_40px]";

export interface JournalLineForm {
  account_id?: number;
  debit?: number;
  credit?: number;
  description?: string;
}

export interface JournalFormValues {
  date: Dayjs;
  reference_no?: string;
  description?: string;
  lines: JournalLineForm[];
}

export function JournalForm({
  initialValues,
  submitLabel,
  pending,
  onSubmit,
  onCancel,
}: {
  initialValues: JournalFormValues;
  submitLabel: string;
  pending: boolean;
  onSubmit: (values: JournalFormValues) => void;
  onCancel: () => void;
}) {
  const { money } = useCurrency();
  const [form] = Form.useForm<JournalFormValues>();
  const accounts = useAccounts();

  const options = (accounts.data ?? [])
    .filter((a) => a.is_postable)
    .map((a) => ({ value: a.id, label: `${a.code} — ${a.name}` }));

  const lines = (Form.useWatch("lines", form) ?? []) as JournalLineForm[];
  const totalDebit = lines.reduce((s, l) => s + Number(l?.debit || 0), 0);
  const totalCredit = lines.reduce((s, l) => s + Number(l?.credit || 0), 0);
  const diff = Math.round((totalDebit - totalCredit) * 10000) / 10000;
  const balanced = diff === 0 && totalDebit > 0;

  return (
    <Card>
      <Form form={form} layout="vertical" onFinish={onSubmit} initialValues={initialValues}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Form.Item name="date" label="Date" rules={[{ required: true }]}>
            <DatePicker className="!w-full" format="DD MMM YYYY" allowClear={false} />
          </Form.Item>
          <Form.Item name="reference_no" label="Reference #">
            <Input placeholder="Optional" />
          </Form.Item>
          <Form.Item name="description" label="Notes">
            <Input placeholder="What is this entry for?" />
          </Form.Item>
        </div>

        <Form.List name="lines">
          {(fields, { add, remove }) => (
            <div className="space-y-2">
              <div className={`hidden ${GRID_COLUMNS} px-1 text-xs text-gray-400 md:grid`}>
                <span>Account</span>
                <span>Description</span>
                <span className="text-right">Debit</span>
                <span className="text-right">Credit</span>
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
                      placeholder="Select account"
                      loading={accounts.isLoading}
                      options={options}
                    />
                  </Form.Item>
                  <Form.Item {...rest} name={[name, "description"]} className="!mb-0">
                    <Input placeholder="Line note" />
                  </Form.Item>
                  <Form.Item {...rest} name={[name, "debit"]} className="!mb-0">
                    <InputNumber className="!w-full" min={0} placeholder="Debit" />
                  </Form.Item>
                  <Form.Item {...rest} name={[name, "credit"]} className="!mb-0">
                    <InputNumber className="!w-full" min={0} placeholder="Credit" />
                  </Form.Item>
                  <Button
                    type="text"
                    danger
                    icon={<Trash2 size={15} />}
                    onClick={() => remove(name)}
                    disabled={fields.length <= 2}
                  />
                </div>
              ))}
              <Button type="dashed" icon={<Plus size={14} />} onClick={() => add({})} block>
                Add line
              </Button>
            </div>
          )}
        </Form.List>

        <div className="mt-4 flex flex-col gap-3 rounded-lg bg-slate-50 p-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-3 text-sm text-gray-500 sm:gap-6">
            <span>
              Debit <b className="tabular-nums text-slate-800">{money(totalDebit)}</b>
            </span>
            <span>
              Credit <b className="tabular-nums text-slate-800">{money(totalCredit)}</b>
            </span>
          </div>
          {balanced ? (
            <Tag color="green">In balance</Tag>
          ) : (
            <Tag color="red">Out by {money(Math.abs(diff))}</Tag>
          )}
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <Button onClick={onCancel}>Cancel</Button>
          <Button type="primary" htmlType="submit" loading={pending} disabled={!balanced}>
            {submitLabel}
          </Button>
        </div>
      </Form>
    </Card>
  );
}
