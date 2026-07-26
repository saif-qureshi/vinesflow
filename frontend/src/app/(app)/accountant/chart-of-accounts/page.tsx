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
  Select,
  Switch,
  Tag,
  TextArea,
} from "@/components/ui";
import { useAccounts, useCreateAccount, useUpdateAccount } from "@/hooks/useAccounting";
import { apiErrorMessage } from "@/lib/api";
import type { Account, AccountType, NormalBalance } from "@/types";

const TYPE_META: Record<AccountType, { label: string; color: string; normal: NormalBalance }> = {
  asset: { label: "Asset", color: "blue", normal: "debit" },
  liability: { label: "Liability", color: "volcano", normal: "credit" },
  equity: { label: "Equity", color: "purple", normal: "credit" },
  income: { label: "Income", color: "green", normal: "credit" },
  expense: { label: "Expense", color: "orange", normal: "debit" },
};

const TYPE_OPTIONS = Object.entries(TYPE_META).map(([value, m]) => ({ value, label: m.label }));

export default function ChartOfAccountsPage() {
  const { message } = App.useApp();
  const accounts = useAccounts();
  const create = useCreateAccount();
  const update = useUpdateAccount();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const [form] = Form.useForm();

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ account_type: "expense", normal_balance: "debit", is_postable: true });
    setOpen(true);
  };

  const openEdit = (account: Account) => {
    setEditing(account);
    form.setFieldsValue({
      name: account.name,
      is_active: account.is_active,
      description: account.description ?? undefined,
    });
    setOpen(true);
  };

  const submit = async (values: Record<string, unknown>) => {
    try {
      if (editing) {
        await update.mutateAsync({
          id: editing.id,
          payload: {
            name: values.name as string,
            is_active: values.is_active as boolean,
            description: (values.description as string) || null,
          },
        });
        message.success("Account updated");
      } else {
        await create.mutateAsync({
          code: values.code as string,
          name: values.name as string,
          account_type: values.account_type as AccountType,
          normal_balance: values.normal_balance as NormalBalance,
          parent_id: (values.parent_id as number) ?? null,
          is_postable: values.is_postable as boolean,
          description: (values.description as string) || null,
        });
        message.success("Account created");
      }
      setOpen(false);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const parentOptions = (accounts.data ?? []).map((a) => ({
    value: a.id,
    label: `${a.code} — ${a.name}`,
  }));

  const columns: ColumnsType<Account> = [
    {
      title: "Code",
      dataIndex: "code",
      key: "code",
      width: 90,
      render: (v) => <span className="font-mono text-slate-500">{v}</span>,
    },
    {
      title: "Account",
      dataIndex: "name",
      key: "name",
      render: (v, a) => (
        <span className={a.is_postable ? "" : "font-semibold"} style={{ opacity: a.is_active ? 1 : 0.5 }}>
          {v}
        </span>
      ),
    },
    {
      title: "Type",
      dataIndex: "account_type",
      key: "type",
      width: 120,
      render: (t: AccountType) => <Tag color={TYPE_META[t].color}>{TYPE_META[t].label}</Tag>,
    },
    {
      title: "Balance",
      dataIndex: "normal_balance",
      key: "normal",
      width: 90,
      render: (n: NormalBalance) => (n === "debit" ? "Dr" : "Cr"),
    },
    {
      title: "",
      key: "flags",
      width: 150,
      render: (_, a) => (
        <div className="flex gap-1">
          {a.is_control_account && <Tag color="geekblue">Control</Tag>}
          {!a.is_postable && <Tag>Header</Tag>}
          {!a.is_active && <Tag color="red">Inactive</Tag>}
        </div>
      ),
    },
    {
      title: "Actions",
      key: "actions",
      align: "right",
      width: 90,
      render: (_, a) => (
        <Button size="small" type="text" onClick={() => openEdit(a)}>
          Edit
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Chart of Accounts"
        description="The ledger accounts every transaction posts to"
        actions={
          <Button type="primary" icon={<Plus size={16} />} onClick={openCreate}>
            New account
          </Button>
        }
      />
      <DataTable<Account>
        rowKey="id"
        columns={columns}
        dataSource={accounts.data ?? []}
        loading={accounts.isLoading}
        pagination={false}
      />
      <FormModal
        title={editing ? "Edit account" : "New account"}
        open={open}
        form={form}
        onCancel={() => setOpen(false)}
        onSubmit={submit}
        confirmLoading={create.isPending || update.isPending}
      >
        {!editing && (
          <>
            <Form.Item name="code" label="Code" rules={[{ required: true }]}>
              <Input placeholder="e.g. 5210" />
            </Form.Item>
            <Form.Item name="account_type" label="Type" rules={[{ required: true }]}>
              <Select
                options={TYPE_OPTIONS}
                onChange={(t: AccountType) =>
                  form.setFieldValue("normal_balance", TYPE_META[t].normal)
                }
              />
            </Form.Item>
            <Form.Item name="normal_balance" label="Normal balance" rules={[{ required: true }]}>
              <Select
                options={[
                  { value: "debit", label: "Debit" },
                  { value: "credit", label: "Credit" },
                ]}
              />
            </Form.Item>
            <Form.Item name="parent_id" label="Parent account">
              <Select allowClear showSearch optionFilterProp="label" options={parentOptions} />
            </Form.Item>
            <Form.Item name="is_postable" label="Postable" valuePropName="checked">
              <Switch />
            </Form.Item>
          </>
        )}
        <Form.Item name="name" label="Name" rules={[{ required: true }]}>
          <Input placeholder="e.g. Rent Expense" />
        </Form.Item>
        <Form.Item name="description" label="Description">
          <TextArea rows={2} />
        </Form.Item>
        {editing && (
          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        )}
      </FormModal>
    </div>
  );
}
