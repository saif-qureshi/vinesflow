"use client";

import { Button, Card, Form, Input, Select, Space, Switch, Typography } from "antd";
import { ArrowLeft, Building2, Save, UserRound } from "lucide-react";

export interface OrganizationFormValues {
  name: string;
  currency: string;
  country: string;
  industry?: string;
  fiscal_year_start_month: number;
  is_active?: boolean;
  owner_full_name?: string;
  owner_email?: string;
  owner_password?: string;
}

interface OrganizationFormProps {
  mode: "create" | "edit";
  initialValues?: Partial<OrganizationFormValues>;
  submitting: boolean;
  onCancel: () => void;
  onSubmit: (values: OrganizationFormValues) => Promise<void>;
}

const months = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
].map((label, index) => ({ label, value: index + 1 }));

export function OrganizationForm({
  mode,
  initialValues,
  submitting,
  onCancel,
  onSubmit,
}: OrganizationFormProps) {
  const creating = mode === "create";

  return (
    <Form<OrganizationFormValues>
      layout="vertical"
      requiredMark={false}
      initialValues={{
        currency: "PKR",
        country: "PK",
        fiscal_year_start_month: 7,
        is_active: true,
        ...initialValues,
      }}
      onFinish={(values) => void onSubmit(values)}
    >
      <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div className="flex items-start gap-3">
          <Button
            type="text"
            icon={<ArrowLeft size={19} />}
            onClick={onCancel}
            aria-label="Go back"
          />
          <div>
            <Typography.Title level={2} className="!mb-1 !text-3xl">
              {creating ? "New organization" : "Edit organization"}
            </Typography.Title>
            <Typography.Text type="secondary">
              {creating
                ? "Create the organization and its first owner account."
                : "Update organization settings and platform access."}
            </Typography.Text>
          </div>
        </div>
        <Space>
          <Button onClick={onCancel}>Cancel</Button>
          <Button type="primary" htmlType="submit" icon={<Save size={17} />} loading={submitting}>
            {creating ? "Create organization" : "Save changes"}
          </Button>
        </Space>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <Card
          title={
            <Space>
              <Building2 size={18} />
              Organization details
            </Space>
          }
          className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]"
        >
          <div className="grid grid-cols-1 gap-x-5 md:grid-cols-2">
            <Form.Item
              name="name"
              label="Organization name"
              rules={[{ required: true, message: "Enter the organization name" }]}
              className="md:col-span-2"
            >
              <Input placeholder="Acme Distribution" />
            </Form.Item>
            <Form.Item name="industry" label="Industry">
              <Input placeholder="Distribution" />
            </Form.Item>
            <Form.Item
              name="fiscal_year_start_month"
              label="Fiscal year starts"
              rules={[{ required: true }]}
            >
              <Select options={months} />
            </Form.Item>
            <Form.Item
              name="country"
              label="Country code"
              rules={[{ required: true, len: 2, message: "Use a 2-letter country code" }]}
            >
              <Input maxLength={2} className="uppercase" placeholder="PK" />
            </Form.Item>
            <Form.Item
              name="currency"
              label="Currency"
              rules={[{ required: true, len: 3, message: "Use a 3-letter currency code" }]}
            >
              <Input maxLength={3} className="uppercase" placeholder="PKR" />
            </Form.Item>
          </div>
        </Card>

        {creating ? (
          <Card
            title={
              <Space>
                <UserRound size={18} />
                Owner account
              </Space>
            }
            className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]"
          >
            <Form.Item name="owner_full_name" label="Owner name">
              <Input placeholder="Full name" autoComplete="name" />
            </Form.Item>
            <Form.Item
              name="owner_email"
              label="Owner email"
              rules={[{ required: true, type: "email", message: "Enter a valid email" }]}
            >
              <Input placeholder="owner@company.com" autoComplete="email" />
            </Form.Item>
            <Form.Item
              name="owner_password"
              label="Temporary password"
              extra="Share this securely with the organization owner."
              rules={[{ required: true, min: 8, message: "Use at least 8 characters" }]}
            >
              <Input.Password autoComplete="new-password" />
            </Form.Item>
          </Card>
        ) : (
          <Card
            title="Platform access"
            className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]"
          >
            <div className="flex items-center justify-between gap-6">
              <div>
                <div className="font-medium text-slate-900">Organization enabled</div>
                <div className="mt-1 text-sm text-slate-500">
                  Disabled organizations cannot be accessed by their members.
                </div>
              </div>
              <Form.Item name="is_active" valuePropName="checked" noStyle>
                <Switch />
              </Form.Item>
            </div>
          </Card>
        )}
      </div>
    </Form>
  );
}
