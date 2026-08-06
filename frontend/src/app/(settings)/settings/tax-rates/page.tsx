"use client";

import { useState } from "react";
import { InputNumber } from "antd";
import { Plus } from "lucide-react";
import type { ColumnsType } from "antd/es/table";

import {
  App,
  Button,
  DataTable,
  Form,
  FormModal,
  Input,
  PageHeader,
  Switch,
  Tag,
} from "@/components/ui";
import { errorState } from "@/components/ui/QueryFallback";
import { useCreateTaxRate, useTaxRates, useUpdateTaxRate } from "@/hooks/useDocuments";
import { useCan } from "@/hooks/useSession";
import { apiErrorMessage } from "@/lib/api";
import type { TaxRate } from "@/types";

interface FormValues {
  name: string;
  rate: number;
  is_active: boolean;
}

export default function TaxRatesSettingsPage() {
  const { message } = App.useApp();
  const can = useCan();
  const rates = useTaxRates();
  const create = useCreateTaxRate();
  const update = useUpdateTaxRate();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<TaxRate | null>(null);
  const [form] = Form.useForm<FormValues>();

  const canEdit = can("orgs:update");

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true });
    setOpen(true);
  };

  const openEdit = (rate: TaxRate) => {
    setEditing(rate);
    form.setFieldsValue({
      name: rate.name,
      rate: Number(rate.rate),
      is_active: rate.is_active,
    });
    setOpen(true);
  };

  const submit = async (values: FormValues) => {
    try {
      if (editing) await update.mutateAsync({ id: editing.id, payload: values });
      else await create.mutateAsync(values);
      message.success(editing ? "Tax rate updated" : "Tax rate created");
      setOpen(false);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const toggle = async (rate: TaxRate, is_active: boolean) => {
    try {
      await update.mutateAsync({ id: rate.id, payload: { is_active } });
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const columns: ColumnsType<TaxRate> = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      render: (value, rate) => (
        <span className="font-medium">
          {value} {rate.is_system && <Tag className="ml-1">Built-in</Tag>}
        </span>
      ),
    },
    {
      title: "Rate",
      dataIndex: "rate",
      key: "rate",
      align: "right",
      render: (value) => <span className="tabular-nums">{Number(value)}%</span>,
    },
    {
      title: "Active",
      key: "is_active",
      render: (_, rate) => (
        <Switch
          size="small"
          checked={rate.is_active}
          disabled={!canEdit}
          onChange={(checked) => toggle(rate, checked)}
        />
      ),
    },
    {
      title: "Actions",
      key: "actions",
      align: "right",
      render: (_, rate) =>
        canEdit && (
          <Button size="small" type="text" onClick={() => openEdit(rate)}>
            Edit
          </Button>
        ),
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Tax Rates"
        description="The rates available on document lines"
        actions={
          canEdit && (
            <Button type="primary" icon={<Plus size={16} />} onClick={openCreate}>
              New tax rate
            </Button>
          )
        }
      />
      {rates.error && errorState(rates.error)}
      <DataTable<TaxRate>
        columns={columns}
        dataSource={rates.data ?? []}
        loading={rates.isLoading}
      />
      <FormModal
        title={editing ? "Edit tax rate" : "New tax rate"}
        open={open}
        form={form}
        onCancel={() => setOpen(false)}
        onSubmit={submit}
        confirmLoading={create.isPending || update.isPending}
      >
        <Form.Item name="name" label="Name" rules={[{ required: true }]}>
          <Input placeholder="e.g. GST 18%" />
        </Form.Item>
        <Form.Item
          name="rate"
          label="Rate (%)"
          rules={[{ required: true, message: "Enter a percentage" }]}
          extra={
            editing
              ? "A rate already used on documents cannot be repriced — add a new one instead."
              : undefined
          }
        >
          <InputNumber min={0} max={100} step={0.5} className="!w-full" />
        </Form.Item>
        <Form.Item name="is_active" label="Active" valuePropName="checked">
          <Switch />
        </Form.Item>
      </FormModal>
    </div>
  );
}
