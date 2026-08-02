"use client";

import { Button, Card, Form, Input, Select, Space, Switch, Typography } from "antd";
import { ArrowLeft, Building2, Save, UserRound } from "lucide-react";

import { OrganizationLogoUploader } from "@/components/OrganizationLogoUploader";

export interface OrganizationFormValues {
  name: string;
  currency: string;
  country: string;
  industry?: string;
  ntn?: string;
  strn?: string;
  cnic?: string;
  logo_url?: string;
  address_attention?: string;
  address_line1?: string;
  address_line2?: string;
  address_city?: string;
  address_state?: string;
  address_country?: string;
  address_postal_code?: string;
  address_phone?: string;
  fbr_enabled?: boolean;
  fbr_environment?: "sandbox" | "production";
  fbr_province?: string;
  fbr_sandbox_token?: string;
  fbr_production_token?: string;
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
  sandboxConfigured?: boolean;
  productionConfigured?: boolean;
  organizationId?: number;
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
  sandboxConfigured = false,
  productionConfigured = false,
  organizationId,
}: OrganizationFormProps) {
  const creating = mode === "create";

  return (
    <Form<OrganizationFormValues>
      layout="vertical"
      requiredMark={false}
      initialValues={{
        currency: "PKR",
        country: "PK",
        address_country: "Pakistan",
        fiscal_year_start_month: 7,
        is_active: true,
        fbr_enabled: false,
        fbr_environment: "sandbox",
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
        <div className="grid content-start gap-6">
          <Card
            title={
              <Space>
                <Building2 size={18} />
                Identity and registration
              </Space>
            }
            className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]"
          >
            <div className="grid grid-cols-1 gap-x-5 md:grid-cols-2">
              <Form.Item
                name="name"
                label="Organization name"
                rules={[{ required: true, message: "Enter the organization name" }]}
              >
                <Input placeholder="Acme Distribution" />
              </Form.Item>
              <Form.Item name="industry" label="Industry">
                <Input placeholder="Distribution" />
              </Form.Item>

              {!creating && (
                <>
                  {organizationId && (
                    <Form.Item
                      name="logo_url"
                      label="Organization logo"
                      className="md:col-span-2"
                      extra="PNG, JPEG, WebP or GIF. Maximum 5MB."
                      getValueProps={(url?: string) => ({ value: url ? [url] : [] })}
                      getValueFromEvent={(urls: string[]) => urls[0] ?? ""}
                    >
                      <OrganizationLogoUploader organizationId={organizationId} />
                    </Form.Item>
                  )}
                  <Form.Item name="ntn" label="NTN">
                    <Input maxLength={20} placeholder="National tax number" />
                  </Form.Item>
                  <Form.Item name="strn" label="STRN">
                    <Input maxLength={20} placeholder="Sales tax registration number" />
                  </Form.Item>
                  <Form.Item name="cnic" label="CNIC">
                    <Input maxLength={20} placeholder="Owner or proprietor CNIC" />
                  </Form.Item>
                </>
              )}
            </div>
          </Card>

          {!creating && (
            <Card
              title="Registered address"
              className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]"
            >
              <div className="grid grid-cols-1 gap-x-5 md:grid-cols-2">
                <Form.Item name="address_attention" label="Attention">
                  <Input placeholder="Accounts department" />
                </Form.Item>
                <Form.Item name="address_phone" label="Phone">
                  <Input placeholder="+92 300 0000000" />
                </Form.Item>
                <Form.Item name="address_line1" label="Address line 1" className="md:col-span-2">
                  <Input placeholder="Street and building" />
                </Form.Item>
                <Form.Item name="address_line2" label="Address line 2" className="md:col-span-2">
                  <Input placeholder="Area or suite" />
                </Form.Item>
                <Form.Item name="address_city" label="City">
                  <Input placeholder="Karachi" />
                </Form.Item>
                <Form.Item name="address_state" label="Province / state">
                  <Input placeholder="Sindh" />
                </Form.Item>
                <Form.Item name="address_postal_code" label="Postal code">
                  <Input placeholder="74000" />
                </Form.Item>
                <Form.Item name="address_country" label="Country">
                  <Input placeholder="Pakistan" />
                </Form.Item>
              </div>
            </Card>
          )}

          {!creating && (
            <Card
              title="FBR integration"
              className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]"
            >
              <div className="mb-5 flex items-center justify-between gap-6 rounded-lg border border-slate-200 p-4">
                <div>
                  <div className="font-medium text-slate-900">FBR e-invoicing enabled</div>
                  <div className="mt-1 text-sm text-slate-500">
                    Controls FBR validation and submission for this organization.
                  </div>
                </div>
                <Form.Item name="fbr_enabled" valuePropName="checked" noStyle>
                  <Switch />
                </Form.Item>
              </div>
              <div className="grid grid-cols-1 gap-x-5 md:grid-cols-2">
                <Form.Item name="fbr_environment" label="Active environment">
                  <Select
                    options={[
                      { value: "sandbox", label: "Sandbox" },
                      { value: "production", label: "Production" },
                    ]}
                  />
                </Form.Item>
                <Form.Item name="fbr_province" label="Seller province">
                  <Input placeholder="Sindh" />
                </Form.Item>
                <Form.Item
                  name="fbr_sandbox_token"
                  label="Sandbox token"
                  extra={
                    sandboxConfigured
                      ? "Configured. Leave blank to keep the saved token."
                      : "No sandbox token configured."
                  }
                >
                  <Input.Password autoComplete="new-password" placeholder="Enter a new token" />
                </Form.Item>
                <Form.Item
                  name="fbr_production_token"
                  label="Production token"
                  extra={
                    productionConfigured
                      ? "Configured. Leave blank to keep the saved token."
                      : "No production token configured."
                  }
                >
                  <Input.Password autoComplete="new-password" placeholder="Enter a new token" />
                </Form.Item>
              </div>
            </Card>
          )}
        </div>

        <div className="grid content-start gap-6">
          <Card
            title="Regional settings"
            className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.06)]"
          >
            <Form.Item
              name="country"
              label="Country code"
              rules={[{ required: true, len: 2, message: "Use a 2-letter country code" }]}
            >
              <Input maxLength={2} className="uppercase" placeholder="PK" />
            </Form.Item>
            <Form.Item
              name="currency"
              label="Base currency"
              rules={[{ required: true, len: 3, message: "Use a 3-letter currency code" }]}
            >
              <Input maxLength={3} className="uppercase" placeholder="PKR" />
            </Form.Item>
            <Form.Item
              name="fiscal_year_start_month"
              label="Fiscal year starts"
              rules={[{ required: true }]}
              className="!mb-0"
            >
              <Select options={months} />
            </Form.Item>
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
                className="!mb-0"
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
      </div>
    </Form>
  );
}
