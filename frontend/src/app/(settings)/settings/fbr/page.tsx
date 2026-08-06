"use client";

import { useEffect, useState } from "react";
import { KeyRound, ShieldCheck } from "lucide-react";

import { Alert, App, PageHeader, Password, Radio, Select, Switch, Tag, Typography } from "@/components/ui";
import { SettingRow, SettingsFooter } from "@/components/settings/SettingRow";
import { useCan, useSession } from "@/hooks/useSession";
import { useFbrProvinces } from "@/hooks/useFbr";
import { useUpdateOrg } from "@/hooks/useOrg";
import { useSettingsGroup, useUpdateSettingsGroup } from "@/hooks/useSettings";
import { apiErrorMessage } from "@/lib/api";

export default function FbrSettingsPage() {
  const { currentMembership } = useSession();
  const can = useCan();
  const { message } = App.useApp();
  const updateOrg = useUpdateOrg();
  const provinces = useFbrProvinces();
  const fbrSettings = useSettingsGroup<{ validate_before_submit?: boolean }>("fbr");
  const updateFbrSettings = useUpdateSettingsGroup("fbr");

  const org = currentMembership?.organization;
  const canEdit = can("orgs:update");

  const [enabled, setEnabled] = useState(false);
  const [environment, setEnvironment] = useState<"sandbox" | "production">("sandbox");
  const [province, setProvince] = useState<string | undefined>();
  const [sandboxToken, setSandboxToken] = useState("");
  const [productionToken, setProductionToken] = useState("");
  const [validateBeforeSubmit, setValidateBeforeSubmit] = useState(true);

  useEffect(() => {
    if (!org) return;
    setEnabled(org.fbr_enabled);
    setEnvironment(org.fbr_environment);
    setProvince(org.fbr_province ?? undefined);
    setSandboxToken("");
    setProductionToken("");
  }, [org]);

  useEffect(() => {
    setValidateBeforeSubmit(fbrSettings.data?.validate_before_submit ?? true);
  }, [fbrSettings.data]);

  const activeConfigured =
    environment === "sandbox" ? org?.fbr_sandbox_configured : org?.fbr_production_configured;
  const activeTokenTyped = environment === "sandbox" ? sandboxToken : productionToken;
  const missingActiveToken = enabled && !activeConfigured && !activeTokenTyped.trim();

  const save = async () => {
    if (enabled && !province) {
      message.error("Select the province registered with FBR");
      return;
    }
    try {
      await updateOrg.mutateAsync({
        fbr_enabled: enabled,
        fbr_environment: environment,
        fbr_province: province ?? "",
        ...(sandboxToken.trim() ? { fbr_sandbox_token: sandboxToken.trim() } : {}),
        ...(productionToken.trim() ? { fbr_production_token: productionToken.trim() } : {}),
      });
      await updateFbrSettings.mutateAsync({ validate_before_submit: validateBeforeSubmit });
      setSandboxToken("");
      setProductionToken("");
      message.success("FBR settings saved");
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const disabled = !canEdit || !enabled;

  return (
    <div>
      <PageHeader
        title="FBR e-Invoicing"
        description="Submit sales invoices to Pakistan's FBR Digital Invoicing system."
        actions={
          <Tag color={org?.fbr_enabled ? "green" : "default"} className="!m-0">
            {org?.fbr_enabled ? "Enabled" : "Disabled"}
          </Tag>
        }
      />

      <div className="mt-2">
        <Alert
          type="info"
          showIcon
          icon={<ShieldCheck size={16} />}
          title="Tokens are stored encrypted and never shown again."
          description="Paste the bearer tokens issued by FBR for your NTN. Sandbox is used for validation; production files live invoices. Onboarding scenarios are cleared by the Vineflow team."
          className="!mb-2"
        />

        <SettingRow
          label="Enable FBR e-Invoicing"
          help="When on, finalized sales invoices are submitted to FBR for an Invoice Reference Number."
        >
          <Switch checked={enabled} disabled={!canEdit} onChange={setEnabled} />
        </SettingRow>

        <SettingRow
          label="Active environment"
          help="Which credentials are used when an invoice is submitted."
        >
          <Radio.Group
            value={environment}
            disabled={disabled}
            onChange={(e) => setEnvironment(e.target.value)}
            optionType="button"
            buttonStyle="solid"
            options={[
              { value: "sandbox", label: "Sandbox" },
              { value: "production", label: "Production" },
            ]}
          />
        </SettingRow>

        <SettingRow label="Province" required={enabled} help="The province registered with FBR for this seller.">
          <Select
            value={province}
            onChange={setProvince}
            options={provinces.data ?? []}
            loading={provinces.isLoading}
            showSearch
            optionFilterProp="label"
            allowClear
            placeholder="Select province"
            disabled={disabled}
            className="max-w-md !w-full md:!w-80"
          />
        </SettingRow>

        <SettingRow
          label="Sandbox token"
          help={<TokenState configured={org?.fbr_sandbox_configured} />}
        >
          <Password
            value={sandboxToken}
            onChange={(e) => setSandboxToken(e.target.value)}
            prefix={<KeyRound size={14} className="text-gray-400" />}
            placeholder={org?.fbr_sandbox_configured ? "Leave blank to keep current token" : "Paste sandbox bearer token"}
            autoComplete="off"
            disabled={disabled}
            className="max-w-md"
          />
        </SettingRow>

        <SettingRow
          label="Production token"
          help={<TokenState configured={org?.fbr_production_configured} />}
        >
          <Password
            value={productionToken}
            onChange={(e) => setProductionToken(e.target.value)}
            prefix={<KeyRound size={14} className="text-gray-400" />}
            placeholder={org?.fbr_production_configured ? "Leave blank to keep current token" : "Paste production bearer token"}
            autoComplete="off"
            disabled={disabled}
            className="max-w-md"
          />
        </SettingRow>

        <SettingRow
          label="Require validation before submission"
          help="When on, an invoice must pass FBR validation before it can be submitted."
        >
          <Switch
            checked={validateBeforeSubmit}
            disabled={disabled}
            onChange={setValidateBeforeSubmit}
          />
        </SettingRow>

        {missingActiveToken && (
          <Alert
            type="warning"
            showIcon
            className="!mt-4"
            title={`Add your ${environment} token so invoices can be submitted.`}
          />
        )}

        {canEdit ? (
          <SettingsFooter onSave={save} saving={updateOrg.isPending} />
        ) : (
          <Typography.Paragraph type="secondary" className="!mt-4 !mb-0">
            You don&apos;t have permission to edit FBR settings.
          </Typography.Paragraph>
        )}
      </div>
    </div>
  );
}

function TokenState({ configured }: { configured?: boolean }) {
  return configured ? (
    <Tag color="green" className="!m-0">Configured</Tag>
  ) : (
    <Tag color="default" className="!m-0">Not set</Tag>
  );
}
