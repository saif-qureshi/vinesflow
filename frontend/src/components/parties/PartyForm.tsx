"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Checkbox, Radio, Tabs } from "antd";
import { X } from "lucide-react";

import { AddressAutoComplete, App, Button, Card, Form, Input, MaskedInput, MASKS, PhoneField, Select, TextArea, Typography } from "@/components/ui";
import { Uploader } from "@/components/ui/Uploader";
import { useCurrency } from "@/hooks/useCurrency";
import { useCreateParty, useUpdateParty } from "@/hooks/useParties";
import { apiErrorMessage } from "@/lib/api";
import type { Address, Party, PartyInput, PartyRole } from "@/types";
import { CURRENCIES, PAYMENT_TERMS, SALUTATIONS } from "./constants";

interface FormValues {
  type: "business" | "individual";
  salutation?: string;
  first_name?: string;
  last_name?: string;
  company_name?: string;
  name: string;
  email?: string;
  work_phone?: string;
  mobile?: string;
  roles: PartyRole[];
  currency?: string;
  ntn?: string;
  strn?: string;
  cnic?: string;
  payment_term_days?: number;
  billing_address?: Address;
  shipping_address?: Address;
  notes?: string;
}

const LABEL_COL = { flex: "0 0 160px" } as const;
const WRAPPER_COL = { flex: "1 1 0" } as const;

function cleanAddress(a?: Address): Address | null {
  if (!a) return null;
  return Object.values(a).some((v) => v != null && v !== "") ? a : null;
}

export function PartyForm({ party }: { party?: Party }) {
  const router = useRouter();
  const { message } = App.useApp();
  const { currency } = useCurrency();
  const create = useCreateParty();
  const update = useUpdateParty();
  const [form] = Form.useForm<FormValues>();
  const [avatar, setAvatar] = useState<string[]>(() => (party?.avatar_url ? [party.avatar_url] : []));

  const isEdit = !!party;
  const type = Form.useWatch("type", form);
  const saving = create.isPending || update.isPending;
  const backHref = isEdit ? `/parties/${party.id}` : "/parties";

  useEffect(() => {
    if (!party) return;
    form.setFieldsValue({
      type: party.type,
      salutation: party.salutation ?? undefined,
      first_name: party.first_name ?? undefined,
      last_name: party.last_name ?? undefined,
      company_name: party.company_name ?? undefined,
      name: party.name,
      email: party.email ?? undefined,
      work_phone: party.work_phone ?? undefined,
      mobile: party.mobile ?? undefined,
      roles: [
        ...(party.is_customer ? (["customer"] as PartyRole[]) : []),
        ...(party.is_vendor ? (["vendor"] as PartyRole[]) : []),
      ],
      currency: party.currency ?? undefined,
      ntn: party.ntn ?? undefined,
      strn: party.strn ?? undefined,
      cnic: party.cnic ?? undefined,
      payment_term_days: party.payment_term_days ?? undefined,
      billing_address: party.billing_address ?? undefined,
      shipping_address: party.shipping_address ?? undefined,
      notes: party.notes ?? undefined,
    });
  }, [party, form]);

  const copyBillingToShipping = () =>
    form.setFieldValue("shipping_address", form.getFieldValue("billing_address"));

  const submit = async (values: FormValues) => {
    const roles = values.roles ?? [];
    const payload: PartyInput = {
      type: values.type,
      name: values.name,
      avatar_url: avatar[0] || null,
      company_name: values.company_name || null,
      salutation: values.salutation || null,
      first_name: values.first_name || null,
      last_name: values.last_name || null,
      email: values.email || null,
      work_phone: values.work_phone || null,
      mobile: values.mobile || null,
      currency: values.currency || null,
      ntn: values.ntn || null,
      strn: values.strn || null,
      cnic: values.cnic || null,
      payment_term_days: values.payment_term_days ?? null,
      billing_address: cleanAddress(values.billing_address),
      shipping_address: cleanAddress(values.shipping_address),
      notes: values.notes || null,
      is_active: party?.is_active ?? true,
      is_customer: roles.includes("customer"),
      is_vendor: roles.includes("vendor"),
    };
    try {
      if (isEdit) await update.mutateAsync({ id: party.id, payload });
      else await create.mutateAsync(payload);
      message.success(isEdit ? "Party updated" : "Party created");
      router.push(backHref);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const tabs = [
    {
      key: "other",
      label: "Other Details",
      children: (
        <div className="grid grid-cols-1 gap-x-8 md:grid-cols-2">
          <Form.Item name="currency" label="Currency">
            <Select disabled options={CURRENCIES.map((c) => ({ value: c, label: c }))} />
          </Form.Item>
          <Form.Item name="payment_term_days" label="Payment terms">
            <Select allowClear placeholder="Select terms" options={PAYMENT_TERMS} />
          </Form.Item>
          <Form.Item name="ntn" label="NTN">
            <MaskedInput mask={MASKS.ntn} placeholder="1234567-8" />
          </Form.Item>
          {type === "individual" ? (
            <Form.Item name="cnic" label="CNIC">
              <MaskedInput mask={MASKS.cnic} placeholder="00000-0000000-0" />
            </Form.Item>
          ) : (
            <Form.Item name="strn" label="STRN">
              <MaskedInput mask={MASKS.strn} placeholder="13-digit number" />
            </Form.Item>
          )}
        </div>
      ),
    },
    {
      key: "address",
      label: "Address",
      children: (
        <div className="space-y-6">
          <div>
            <div className="mb-3 text-sm font-medium">Billing address</div>
            <Form.Item name="billing_address" noStyle>
              <AddressAutoComplete />
            </Form.Item>
          </div>
          <div>
            <div className="mb-3 flex items-center justify-between">
              <span className="text-sm font-medium">Shipping address</span>
              <Button type="link" size="small" className="!px-0" onClick={copyBillingToShipping}>
                Copy billing address
              </Button>
            </div>
            <Form.Item name="shipping_address" noStyle>
              <AddressAutoComplete />
            </Form.Item>
          </div>
        </div>
      ),
    },
    {
      key: "remarks",
      label: "Remarks",
      children: (
        <Form.Item name="notes" labelCol={{ span: 24 }} wrapperCol={{ span: 24 }} noStyle>
          <TextArea rows={4} placeholder="Notes for internal use" />
        </Form.Item>
      ),
    },
  ];

  return (
    <Form<FormValues>
      form={form}
      layout="horizontal"
      labelAlign="left"
      labelCol={LABEL_COL}
      wrapperCol={WRAPPER_COL}
      colon={false}
      onFinish={submit}
      initialValues={{
        type: "business",
        currency,
        payment_term_days: 0,
        roles: [],
      }}
      className="flex flex-col gap-6 pb-24"
    >
      <div className="flex items-center justify-between">
        <Typography.Title level={3} className="!mb-0">
          {isEdit ? "Edit Party" : "New Party"}
        </Typography.Title>
        <Button type="text" icon={<X size={18} />} onClick={() => router.push(backHref)} />
      </div>

      <Card title="Primary Details" className="border-gray-100">
        <Form.Item label="Photo">
          <Uploader
            value={avatar}
            onChange={setAvatar}
            maxCount={1}
            accept="image/*"
            maxSizeMB={5}
            drag={false}
          />
        </Form.Item>

        <Form.Item name="type" label="Party type">
          <Radio.Group
            options={[
              { label: "Business", value: "business" },
              { label: "Individual", value: "individual" },
            ]}
          />
        </Form.Item>

        <Form.Item label="Primary contact">
          <div className="flex gap-2">
            <Form.Item name="salutation" noStyle>
              <Select
                className="!w-24"
                placeholder="Title"
                allowClear
                options={SALUTATIONS.map((s) => ({ value: s, label: s }))}
              />
            </Form.Item>
            <Form.Item name="first_name" noStyle>
              <Input placeholder="First name" />
            </Form.Item>
            <Form.Item name="last_name" noStyle>
              <Input placeholder="Last name" />
            </Form.Item>
          </div>
        </Form.Item>

        <div className="grid grid-cols-1 gap-x-8 md:grid-cols-2">
          <Form.Item name="company_name" label="Company name">
            <Input placeholder="Company name" />
          </Form.Item>
          <Form.Item
            name="name"
            label="Display name"
            rules={[{ required: true, message: "Display name is required" }]}
          >
            <Input placeholder="Shown across the app" />
          </Form.Item>
          <Form.Item name="email" label="Email">
            <Input type="email" placeholder="name@company.com" />
          </Form.Item>
        </div>

        <Form.Item label="Phone">
          <div className="flex gap-2">
            <Form.Item name="work_phone" noStyle>
              <PhoneField placeholder="Work phone" />
            </Form.Item>
            <Form.Item name="mobile" noStyle>
              <PhoneField placeholder="Mobile" />
            </Form.Item>
          </div>
        </Form.Item>

        <Form.Item
          name="roles"
          label="Roles"
          rules={[{ required: true, message: "Select at least one role" }]}
        >
          <Checkbox.Group
            options={[
              { label: "Customer", value: "customer" },
              { label: "Vendor", value: "vendor" },
            ]}
          />
        </Form.Item>
      </Card>

      <Card className="border-gray-100">
        <Tabs items={tabs} />
      </Card>

      <div className="sticky bottom-0 flex gap-3 border-t border-gray-100 bg-slate-50 px-6 py-3">
        <Button type="primary" htmlType="submit" loading={saving}>
          {isEdit ? "Save" : "Create Party"}
        </Button>
        <Button onClick={() => router.push(backHref)}>Cancel</Button>
      </div>
    </Form>
  );
}
