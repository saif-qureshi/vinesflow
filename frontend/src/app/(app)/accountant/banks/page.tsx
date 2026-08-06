"use client";

import { useState } from "react";
import { Switch } from "antd";
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
  Select,
  Tag,
} from "@/components/ui";
import { errorState } from "@/components/ui/QueryFallback";
import { BankBadge } from "@/components/banks/BankBadge";
import {
  useBankAccounts,
  useBankCatalog,
  useCreateBankAccount,
  useDeleteBankAccount,
  useUpdateBankAccount,
} from "@/hooks/useBanks";
import { useCurrency } from "@/hooks/useCurrency";
import { useCan } from "@/hooks/useSession";
import { apiErrorMessage } from "@/lib/api";
import { validateIban } from "@/lib/iban";
import type { BankAccount } from "@/types";

interface FormValues {
  bank_name: string;
  account_title: string;
  account_number: string;
  iban?: string;
  branch?: string;
  is_active?: boolean;
}

export default function BanksPage() {
  const { message } = App.useApp();
  const { money } = useCurrency();
  const can = useCan();
  const accounts = useBankAccounts();
  const catalog = useBankCatalog();
  const create = useCreateBankAccount();
  const update = useUpdateBankAccount();
  const del = useDeleteBankAccount();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<BankAccount | null>(null);
  const [form] = Form.useForm<FormValues>();

  const canEdit = can("accounting:update");
  const bankOf = (row: BankAccount) =>
    catalog.data?.find((bank) => bank.code === row.bank_code);
  const dash = <span className="text-gray-400">—</span>;

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true });
    setOpen(true);
  };

  const openEdit = (row: BankAccount) => {
    setEditing(row);
    form.setFieldsValue({
      bank_name: row.bank_name,
      account_title: row.account_title,
      account_number: row.account_number,
      iban: row.iban ?? undefined,
      branch: row.branch ?? undefined,
      is_active: row.is_active,
    });
    setOpen(true);
  };

  const submit = async (values: FormValues) => {
    const known = catalog.data?.find((bank) => bank.name === values.bank_name);
    const payload = { ...values, bank_code: known?.code ?? null };
    try {
      if (editing) await update.mutateAsync({ id: editing.id, payload });
      else await create.mutateAsync(payload);
      message.success(`Bank account ${editing ? "updated" : "added"}`);
      setOpen(false);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const remove = async (id: number) => {
    try {
      await del.mutateAsync(id);
      message.success("Bank account removed");
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const columns: ColumnsType<BankAccount> = [
    {
      title: "Bank",
      key: "bank",
      render: (_, row) => (
        <div className="flex items-center gap-3">
          <BankBadge name={row.bank_name} colour={bankOf(row)?.colour} logoUrl={bankOf(row)?.logo_url} />
          <div>
            <div className="font-medium">{row.bank_name}</div>
            <div className="text-xs text-gray-500">{row.account_title}</div>
          </div>
        </div>
      ),
    },
    {
      title: "Account",
      key: "account_number",
      render: (_, row) => (
        <div>
          <div className="tabular-nums">{row.account_number}</div>
          {row.iban && <div className="text-xs text-gray-500">{row.iban}</div>}
        </div>
      ),
    },
    { title: "Branch", key: "branch", render: (_, row) => row.branch || dash },
    {
      title: "Ledger",
      key: "ledger",
      render: (_, row) => (row.account_code ? <Tag>{row.account_code}</Tag> : dash),
    },
    {
      title: "Balance",
      key: "balance",
      align: "right",
      render: (_, row) => (
        <span className="tabular-nums font-medium">{money(Number(row.balance))}</span>
      ),
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
            <Popconfirm title="Remove this bank account?" onConfirm={() => remove(row.id)}>
              <Button size="small" type="text" danger>
                Remove
              </Button>
            </Popconfirm>
          </div>
        ),
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Banks"
        description="Each account keeps its own ledger account, so balances and cash flow stay separate"
        actions={
          can("accounting:create") && (
            <Button type="primary" icon={<Plus size={16} />} onClick={openCreate}>
              Add bank account
            </Button>
          )
        }
      />
      {accounts.error && errorState(accounts.error)}
      <DataTable<BankAccount>
        columns={columns}
        dataSource={accounts.data ?? []}
        loading={accounts.isLoading}
      />
      <FormModal
        title={editing ? "Edit bank account" : "Add bank account"}
        open={open}
        form={form}
        onCancel={() => setOpen(false)}
        onSubmit={submit}
        confirmLoading={create.isPending || update.isPending}
      >
        <Form.Item name="bank_name" label="Bank" rules={[{ required: true }]}>
          <Select
            showSearch
            allowClear={false}
            placeholder="Select or type a bank"
            filterOption={(input, option) =>
              String(option?.title ?? "").toLowerCase().includes(input.toLowerCase())
            }
            options={(catalog.data ?? []).map((bank) => ({
              value: bank.name,
              title: bank.name,
              label: (
                <div className="flex items-center gap-2">
                  <BankBadge
                    name={bank.name}
                    colour={bank.colour}
                    logoUrl={bank.logo_url}
                    size={22}
                  />
                  <span>{bank.name}</span>
                </div>
              ),
            }))}
          />
        </Form.Item>
        <Form.Item
          name="account_title"
          label="Account title"
          rules={[
            { required: true, message: "Enter the name the account is held in" },
            { min: 2, message: "That looks too short" },
          ]}
        >
          <Input placeholder="The name the account is held in" />
        </Form.Item>
        <Form.Item
          name="account_number"
          label="Account number"
          normalize={(value?: string) => value?.replace(/\s/g, "")}
          rules={[
            { required: true, message: "Enter the account number" },
            {
              pattern: /^[0-9][0-9-]{5,29}$/,
              message: "Digits only, 6-30 of them, optionally grouped with dashes",
            },
          ]}
        >
          <Input placeholder="e.g. 0102030405" inputMode="numeric" />
        </Form.Item>
        <Form.Item
          name="iban"
          label="IBAN"
          normalize={(value?: string) => value?.replace(/\s/g, "").toUpperCase()}
          rules={[{ validator: (_, value) => validateIban(value) }]}
        >
          <Input placeholder="PK36SCBL0000001123456702" />
        </Form.Item>
        <Form.Item name="branch" label="Branch">
          <Input placeholder="Optional" />
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
