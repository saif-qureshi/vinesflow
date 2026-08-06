"use client";

import { useState } from "react";
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
  TextArea,
} from "@/components/ui";
import { errorState } from "@/components/ui/QueryFallback";
import {
  useCreateNamed,
  useDeleteNamed,
  useNamedList,
  useUpdateNamed,
} from "@/hooks/useMasterData";
import { useCan } from "@/hooks/useSession";
import { apiErrorMessage } from "@/lib/api";
import type { NamedRecord, NamedRecordInput } from "@/types";

interface MasterDataPageProps {
  resource: string;
  title: string;
  description: string;
  singular: string;
  placeholder: string;
}

export function MasterDataPage({
  resource,
  title,
  description,
  singular,
  placeholder,
}: MasterDataPageProps) {
  const { message } = App.useApp();
  const can = useCan();
  const list = useNamedList(resource);
  const create = useCreateNamed(resource);
  const update = useUpdateNamed(resource);
  const del = useDeleteNamed(resource);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<NamedRecord | null>(null);
  const [form] = Form.useForm();

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true });
    setOpen(true);
  };

  const openEdit = (row: NamedRecord) => {
    setEditing(row);
    form.setFieldsValue({
      name: row.name,
      description: row.description ?? undefined,
      is_active: row.is_active,
    });
    setOpen(true);
  };

  const submit = async (values: NamedRecordInput) => {
    try {
      if (editing) await update.mutateAsync({ id: editing.id, payload: values });
      else await create.mutateAsync(values);
      message.success(`${singular} ${editing ? "updated" : "created"}`);
      setOpen(false);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const remove = async (id: number) => {
    try {
      await del.mutateAsync(id);
      message.success(`${singular} deleted`);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const columns: ColumnsType<NamedRecord> = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      render: (value) => <span className="font-medium">{value}</span>,
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "description",
      render: (value) => value || <span className="text-gray-400">—</span>,
    },
    {
      title: "Status",
      key: "status",
      render: (_, row) =>
        row.is_active ? <Tag color="green">Active</Tag> : <Tag>Inactive</Tag>,
    },
    {
      title: "Actions",
      key: "actions",
      align: "right",
      render: (_, row) => (
        <div className="flex justify-end gap-1">
          {can("products:update") && (
            <Button size="small" type="text" onClick={() => openEdit(row)}>
              Edit
            </Button>
          )}
          {can("products:delete") && (
            <Popconfirm
              title={`Delete this ${singular.toLowerCase()}?`}
              onConfirm={() => remove(row.id)}
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
    <div className="space-y-4">
      <PageHeader
        title={title}
        description={description}
        actions={
          can("products:create") && (
            <Button type="primary" icon={<Plus size={16} />} onClick={openCreate}>
              New {singular.toLowerCase()}
            </Button>
          )
        }
      />
      {list.error && errorState(list.error)}
      <DataTable<NamedRecord>
        columns={columns}
        dataSource={list.data ?? []}
        loading={list.isLoading}
      />
      <FormModal
        title={editing ? `Edit ${singular.toLowerCase()}` : `New ${singular.toLowerCase()}`}
        open={open}
        form={form}
        onCancel={() => setOpen(false)}
        onSubmit={submit}
        confirmLoading={create.isPending || update.isPending}
      >
        <Form.Item name="name" label="Name" rules={[{ required: true }]}>
          <Input placeholder={placeholder} />
        </Form.Item>
        <Form.Item name="description" label="Description">
          <TextArea rows={2} placeholder="Optional" />
        </Form.Item>
        <Form.Item name="is_active" label="Active" valuePropName="checked">
          <Switch />
        </Form.Item>
      </FormModal>
    </div>
  );
}
