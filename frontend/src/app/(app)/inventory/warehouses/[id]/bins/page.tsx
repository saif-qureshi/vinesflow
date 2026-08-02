"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Switch } from "antd";
import type { ColumnsType } from "antd/es/table";
import { ArrowLeft, Pencil, Plus, Trash2 } from "lucide-react";

import { App, Button, Form, Input, Modal, PageHeader, Table, Tag } from "@/components/ui";
import { useCreateBin, useDeleteBin, useBins, useUpdateBin } from "@/hooks/useBins";
import { useCan } from "@/hooks/useSession";
import { useWarehouses } from "@/hooks/useWarehouses";
import { apiErrorMessage } from "@/lib/api";
import type { Bin } from "@/types";

interface FormValues {
  code: string;
  name: string;
  is_active: boolean;
}

export default function WarehouseBinsPage() {
  const { id } = useParams<{ id: string }>();
  const locationId = Number(id);
  const router = useRouter();
  const { message, modal } = App.useApp();
  const can = useCan();
  const warehouses = useWarehouses();
  const bins = useBins(locationId);
  const create = useCreateBin();
  const update = useUpdateBin();
  const remove = useDeleteBin();
  const [form] = Form.useForm<FormValues>();
  const [editing, setEditing] = useState<Bin | null>(null);
  const [open, setOpen] = useState(false);
  const warehouse = warehouses.data?.find((row) => row.id === locationId);

  useEffect(() => {
    if (!open) return;
    form.resetFields();
    form.setFieldsValue({
      code: editing?.code ?? "",
      name: editing?.name ?? "",
      is_active: editing?.is_active ?? true,
    });
  }, [editing, form, open]);

  const startCreate = () => {
    setEditing(null);
    setOpen(true);
  };

  const startEdit = (bin: Bin) => {
    setEditing(bin);
    setOpen(true);
  };

  const submit = async (values: FormValues) => {
    try {
      if (editing) {
        await update.mutateAsync({ id: editing.id, payload: values });
      } else {
        await create.mutateAsync({ ...values, location_id: locationId });
      }
      message.success(editing ? "Bin updated" : "Bin created");
      setOpen(false);
    } catch (error) {
      message.error(apiErrorMessage(error));
    }
  };

  const confirmDelete = (bin: Bin) => {
    modal.confirm({
      title: "Delete this bin?",
      content: `Bin ${bin.code} can only be deleted when it has no inventory history.`,
      okText: "Delete",
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await remove.mutateAsync(bin.id);
          message.success("Bin deleted");
        } catch (error) {
          message.error(apiErrorMessage(error));
          throw error;
        }
      },
    });
  };

  const columns: ColumnsType<Bin> = [
    {
      title: "Code",
      dataIndex: "code",
      width: 180,
      render: (code: string) => <span className="font-mono font-medium">{code}</span>,
    },
    { title: "Name", dataIndex: "name" },
    {
      title: "Status",
      key: "status",
      width: 130,
      render: (_, bin) => (bin.is_active ? <Tag>Active</Tag> : <Tag>Inactive</Tag>),
    },
    {
      title: "",
      key: "actions",
      width: 100,
      align: "right",
      render: (_, bin) => (
        <div className="flex justify-end gap-1">
          {can("inventory:update") && (
            <Button
              type="text"
              size="small"
              icon={<Pencil size={14} />}
              onClick={() => startEdit(bin)}
            />
          )}
          {can("inventory:delete") && (
            <Button
              type="text"
              size="small"
              danger
              icon={<Trash2 size={14} />}
              onClick={() => confirmDelete(bin)}
            />
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <Button
        type="text"
        icon={<ArrowLeft size={16} />}
        onClick={() => router.push("/inventory/warehouses")}
      >
        Warehouses
      </Button>
      <PageHeader
        title={`Bins — ${warehouse?.name ?? "Warehouse"}`}
        description="Manage shelf and rack locations inside this warehouse."
        actions={
          can("inventory:create") && (
            <Button type="primary" icon={<Plus size={16} />} onClick={startCreate}>
              New bin
            </Button>
          )
        }
      />

      <div className="overflow-hidden rounded-xl border border-gray-100 bg-white">
        <Table<Bin>
          rowKey="id"
          loading={bins.isLoading || warehouses.isLoading}
          columns={columns}
          dataSource={bins.data ?? []}
          pagination={false}
        />
      </div>

      <Modal
        title={editing ? "Edit bin" : "New bin"}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        okText={editing ? "Save" : "Create"}
        confirmLoading={create.isPending || update.isPending}
        destroyOnHidden
      >
        <Form<FormValues> form={form} layout="vertical" onFinish={submit} className="pt-2">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Form.Item
              name="code"
              label="Code"
              rules={[{ required: true, message: "Code is required" }]}
              extra="A short shelf or rack code, unique within this warehouse."
            >
              <Input placeholder="e.g. A-01-03" />
            </Form.Item>
            <Form.Item
              name="name"
              label="Name"
              rules={[{ required: true, message: "Name is required" }]}
            >
              <Input placeholder="e.g. Rack A / Shelf 3" />
            </Form.Item>
          </div>
          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
