"use client";

import { useState } from "react";
import { ColorPicker, Switch } from "antd";
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
import { Uploader } from "@/components/ui/Uploader";
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
import type { BankAccount, UploadedFile } from "@/types";

interface FormValues {
  bank_name: string;
  account_title: string;
  account_number: string;
  iban?: string;
  branch?: string;
  colour?: string | { toHexString: () => string };
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
  const [logo, setLogo] = useState<UploadedFile[]>([]);
  const [form] = Form.useForm<FormValues>();

  const canEdit = can("accounting:update");
  const dash = <span className="text-gray-400">—</span>;

  const openCreate = () => {
    setEditing(null);
    setLogo([]);
    form.resetFields();
    form.setFieldsValue({ is_active: true });
    setOpen(true);
  };

  const openEdit = (row: BankAccount) => {
    setEditing(row);
    setLogo(
      row.logo_key && row.logo_url ? [{ storage_key: row.logo_key, url: row.logo_url }] : [],
    );
    form.setFieldsValue({
      bank_name: row.bank_name,
      account_title: row.account_title,
      account_number: row.account_number,
      iban: row.iban ?? undefined,
      branch: row.branch ?? undefined,
      colour: row.colour ?? undefined,
      is_active: row.is_active,
    });
    setOpen(true);
  };

  /** Picking a bank from the catalogue pre-fills its brand colour. */
  const onPickBank = (name: string) => {
    const known = catalog.data?.find((bank) => bank.name === name);
    if (known) form.setFieldsValue({ colour: known.colour });
  };

  const submit = async (values: FormValues) => {
    const colour =
      typeof values.colour === "object" && values.colour !== null
        ? values.colour.toHexString()
        : values.colour;
    const known = catalog.data?.find((bank) => bank.name === values.bank_name);
    const payload = {
      ...values,
      colour: colour || null,
      bank_code: known?.code ?? null,
      logo_key: logo[0]?.storage_key ?? null,
    };
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
          <BankBadge
            name={row.bank_name}
            colour={row.colour}
            logoUrl={row.logo_url}
            catalogLogo={catalog.data?.find((b) => b.code === row.bank_code)?.logo}
          />
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
            optionFilterProp="label"
            onChange={onPickBank}
            options={(catalog.data ?? []).map((bank) => ({
              value: bank.name,
              label: bank.name,
            }))}
          />
        </Form.Item>
        <Form.Item name="account_title" label="Account title" rules={[{ required: true }]}>
          <Input placeholder="The name the account is held in" />
        </Form.Item>
        <Form.Item name="account_number" label="Account number" rules={[{ required: true }]}>
          <Input placeholder="e.g. 0102030405" />
        </Form.Item>
        <Form.Item name="iban" label="IBAN">
          <Input placeholder="PK00XXXX0000000000000000" />
        </Form.Item>
        <Form.Item name="branch" label="Branch">
          <Input placeholder="Optional" />
        </Form.Item>
        <Form.Item name="colour" label="Brand colour">
          <ColorPicker showText />
        </Form.Item>
        <Form.Item
          label="Logo"
          extra="Only needed to override the logo shipped for this bank."
        >
          <Uploader
            value={logo}
            onChange={setLogo}
            maxCount={1}
            accept="image/*"
            maxSizeMB={2}
            drag={false}
          />
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
