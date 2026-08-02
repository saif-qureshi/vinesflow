"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Checkbox, Switch } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Boxes, Pencil, Plus, Trash2 } from "lucide-react";

import {
  App,
  AddressAutoComplete,
  Button,
  Form,
  Input,
  Modal,
  PageHeader,
  Table,
  Tag,
} from "@/components/ui";
import { useCan } from "@/hooks/useSession";
import {
  useCreateWarehouse,
  useDeleteWarehouse,
  useUpdateWarehouse,
  useWarehouses,
} from "@/hooks/useWarehouses";
import { apiErrorMessage } from "@/lib/api";
import type { Address, Warehouse } from "@/types";

interface FormValues {
  name: string;
  code?: string;
  is_default?: boolean;
  is_active?: boolean;
  address?: Address;
}

export default function WarehousesPage() {
  const router = useRouter();
  const { message, modal } = App.useApp();
  const can = useCan();
  const { data, isLoading } = useWarehouses();
  const create = useCreateWarehouse();
  const update = useUpdateWarehouse();
  const del = useDeleteWarehouse();
  const [form] = Form.useForm<FormValues>();
  const [editing, setEditing] = useState<Warehouse | null>(null);
  const [open, setOpen] = useState(false);

  const canEdit = can("inventory:update");
  const canCreate = can("inventory:create");
  const canDelete = can("inventory:delete");

  useEffect(() => {
    if (!open) return;
    form.setFieldsValue({
      name: editing?.name ?? "",
      code: editing?.code ?? undefined,
      is_default: editing?.is_default ?? false,
      is_active: editing?.is_active ?? true,
      address: editing?.address ?? undefined,
    });
  }, [open, editing, form]);

  const startCreate = () => {
    setEditing(null);
    setOpen(true);
  };
  const startEdit = (w: Warehouse) => {
    setEditing(w);
    setOpen(true);
  };

  const submit = async (values: FormValues) => {
    const payload = { ...values, address: values.address ?? null };
    try {
      if (editing) await update.mutateAsync({ id: editing.id, payload });
      else await create.mutateAsync(payload);
      message.success(editing ? "Warehouse updated" : "Warehouse created");
      setOpen(false);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const confirmDelete = (w: Warehouse) => {
    modal.confirm({
      title: "Delete this warehouse?",
      content: `"${w.name}" will be removed.`,
      okText: "Delete",
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await del.mutateAsync(w.id);
          message.success("Warehouse deleted");
        } catch (err) {
          message.error(apiErrorMessage(err));
          throw err;
        }
      },
    });
  };

  const addressLabel = (a: Address | null) => {
    if (!a) return <span className="text-gray-400">—</span>;
    return [a.line1, a.city, a.country].filter(Boolean).join(", ") || <span className="text-gray-400">—</span>;
  };

  const columns: ColumnsType<Warehouse> = [
    {
      title: "Name",
      key: "name",
      render: (_, w) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{w.name}</span>
          {w.is_default && <Tag color="blue">Default</Tag>}
        </div>
      ),
    },
    { title: "Code", key: "code", render: (_, w) => w.code || <span className="text-gray-400">—</span> },
    { title: "Address", key: "address", render: (_, w) => addressLabel(w.address) },
    {
      title: "Status",
      key: "status",
      render: (_, w) => (w.is_active ? <Tag color="green">Active</Tag> : <Tag>Inactive</Tag>),
    },
    {
      title: "",
      key: "actions",
      width: 132,
      align: "right",
      render: (_, w) => (
        <div className="flex justify-end gap-1">
          {canEdit && (
            <Button
              type="text"
              size="small"
              icon={<Boxes size={14} />}
              onClick={() => router.push(`/inventory/warehouses/${w.id}/bins`)}
            />
          )}
          {canEdit && (
            <Button type="text" size="small" icon={<Pencil size={14} />} onClick={() => startEdit(w)} />
          )}
          {canDelete && (
            <Button
              type="text"
              size="small"
              danger
              icon={<Trash2 size={14} />}
              onClick={() => confirmDelete(w)}
            />
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Warehouses"
        description="Stock is tracked per warehouse."
        actions={
          canCreate && (
            <Button type="primary" icon={<Plus size={16} />} onClick={startCreate}>
              New Warehouse
            </Button>
          )
        }
      />

      <div className="overflow-hidden rounded-xl border border-gray-100 bg-white">
        <Table<Warehouse>
          rowKey="id"
          loading={isLoading}
          columns={columns}
          dataSource={data ?? []}
          pagination={false}
        />
      </div>

      <Modal
        title={editing ? "Edit Warehouse" : "New Warehouse"}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        okText={editing ? "Save" : "Create"}
        confirmLoading={create.isPending || update.isPending}
        destroyOnHidden
        width={620}
      >
        <Form<FormValues> form={form} layout="vertical" onFinish={submit} className="pt-2">
          <div className="grid grid-cols-1 gap-x-4 md:grid-cols-2">
            <Form.Item name="name" label="Name" rules={[{ required: true, message: "Name is required" }]}>
              <Input placeholder="e.g. Main Warehouse" />
            </Form.Item>
            <Form.Item name="code" label="Code">
              <Input placeholder="e.g. WH-01" />
            </Form.Item>
          </div>
          <Form.Item name="address" label="Address" noStyle>
            <AddressAutoComplete />
          </Form.Item>
          <div className="mt-4 flex items-center gap-6">
            <Form.Item name="is_default" valuePropName="checked" noStyle>
              <Checkbox>Default warehouse</Checkbox>
            </Form.Item>
            <Form.Item name="is_active" valuePropName="checked" label="Active" className="!mb-0">
              <Switch />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </div>
  );
}
