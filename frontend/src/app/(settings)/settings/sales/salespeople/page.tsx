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
  Popconfirm,
  Switch,
  Tag,
} from "@/components/ui";
import { errorState } from "@/components/ui/QueryFallback";
import {
  useCreateSalesperson,
  useDeleteSalesperson,
  useSalespeople,
  useUpdateSalesperson,
} from "@/hooks/useSalespeople";
import { useCan } from "@/hooks/useSession";
import { apiErrorMessage } from "@/lib/api";
import type { Salesperson, SalespersonInput } from "@/types";

export default function SalespeopleSettingsPage() {
  const { message } = App.useApp();
  const can = useCan();
  const list = useSalespeople();
  const create = useCreateSalesperson();
  const update = useUpdateSalesperson();
  const del = useDeleteSalesperson();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Salesperson | null>(null);
  const [form] = Form.useForm<SalespersonInput>();

  const canEdit = can("orgs:update");

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true, commission_rate: 0 });
    setOpen(true);
  };

  const openEdit = (row: Salesperson) => {
    setEditing(row);
    form.setFieldsValue({
      name: row.name,
      email: row.email ?? undefined,
      phone: row.phone ?? undefined,
      commission_rate: Number(row.commission_rate),
      is_active: row.is_active,
    });
    setOpen(true);
  };

  const submit = async (values: SalespersonInput) => {
    try {
      if (editing) await update.mutateAsync({ id: editing.id, payload: values });
      else await create.mutateAsync(values);
      message.success(`Salesperson ${editing ? "updated" : "created"}`);
      setOpen(false);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const remove = async (id: number) => {
    try {
      await del.mutateAsync(id);
      message.success("Salesperson deleted");
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const dash = <span className="text-gray-400">—</span>;

  const columns: ColumnsType<Salesperson> = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      render: (value) => <span className="font-medium">{value}</span>,
    },
    { title: "Email", dataIndex: "email", key: "email", render: (v) => v || dash },
    { title: "Phone", dataIndex: "phone", key: "phone", render: (v) => v || dash },
    {
      title: "Commission",
      dataIndex: "commission_rate",
      key: "commission_rate",
      align: "right",
      render: (value) => <span className="tabular-nums">{Number(value)}%</span>,
    },
    {
      title: "Status",
      key: "status",
      render: (_, row) => (row.is_active ? <Tag color="green">Active</Tag> : <Tag>Inactive</Tag>),
    },
    {
      title: "Actions",
      key: "actions",
      align: "right",
      render: (_, row) =>
        canEdit && (
          <div className="flex justify-end gap-1">
            <Button size="small" type="text" onClick={() => openEdit(row)}>
              Edit
            </Button>
            <Popconfirm title="Delete this salesperson?" onConfirm={() => remove(row.id)}>
              <Button size="small" type="text" danger>
                Delete
              </Button>
            </Popconfirm>
          </div>
        ),
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Salespeople"
        description="Who gets credited for a sale, and what they earn on it"
        actions={
          canEdit && (
            <Button type="primary" icon={<Plus size={16} />} onClick={openCreate}>
              New salesperson
            </Button>
          )
        }
      />
      {list.error && errorState(list.error)}
      <DataTable<Salesperson>
        columns={columns}
        dataSource={list.data ?? []}
        loading={list.isLoading}
      />
      <FormModal
        title={editing ? "Edit salesperson" : "New salesperson"}
        open={open}
        form={form}
        onCancel={() => setOpen(false)}
        onSubmit={submit}
        confirmLoading={create.isPending || update.isPending}
      >
        <Form.Item name="name" label="Name" rules={[{ required: true }]}>
          <Input placeholder="e.g. Ali Raza" />
        </Form.Item>
        <Form.Item name="email" label="Email">
          <Input type="email" placeholder="Optional" />
        </Form.Item>
        <Form.Item name="phone" label="Phone">
          <Input placeholder="Optional" />
        </Form.Item>
        <Form.Item
          name="commission_rate"
          label="Commission rate (%)"
          extra="Applied to the value of a sale excluding tax, fixed at the moment an invoice is finalized."
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
