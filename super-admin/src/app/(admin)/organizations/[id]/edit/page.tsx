"use client";

import { App, Result, Spin } from "antd";
import { useParams, useRouter } from "next/navigation";

import {
  OrganizationForm,
  type OrganizationFormValues,
} from "@/components/OrganizationForm";
import { useOrganization, useUpdateOrganization } from "@/hooks/useSuperAdmin";
import { apiErrorMessage } from "@/lib/api";

export default function EditOrganizationPage() {
  const params = useParams<{ id: string }>();
  const organizationId = Number(params.id);
  const { data: organization, isLoading, isError } = useOrganization(organizationId);
  const update = useUpdateOrganization(organizationId);
  const router = useRouter();
  const { message } = App.useApp();

  if (isLoading) {
    return <div className="flex min-h-80 items-center justify-center"><Spin size="large" /></div>;
  }
  if (isError || !organization) {
    return <Result status="404" title="Organization not found" />;
  }

  const submit = async (values: OrganizationFormValues) => {
    const clean = (value?: string) => value?.trim() || undefined;
    try {
      await update.mutateAsync({
        name: values.name.trim(),
        currency: values.currency.toUpperCase(),
        country: values.country.toUpperCase(),
        industry: clean(values.industry),
        ntn: clean(values.ntn),
        strn: clean(values.strn),
        cnic: clean(values.cnic),
        logo_url: clean(values.logo_url),
        fbr_enabled: values.fbr_enabled,
        fbr_environment: values.fbr_environment,
        fbr_province: clean(values.fbr_province),
        fbr_sandbox_token: clean(values.fbr_sandbox_token),
        fbr_production_token: clean(values.fbr_production_token),
        address: {
          attention: clean(values.address_attention),
          line1: clean(values.address_line1),
          line2: clean(values.address_line2),
          city: clean(values.address_city),
          state: clean(values.address_state),
          country: clean(values.address_country),
          postal_code: clean(values.address_postal_code),
          phone: clean(values.address_phone),
        },
        fiscal_year_start_month: values.fiscal_year_start_month,
        is_active: values.is_active ?? organization.is_active,
      });
      message.success("Organization updated");
      router.replace(`/organizations/${organization.id}`);
    } catch (error) {
      message.error(apiErrorMessage(error, "Could not update organization"));
    }
  };

  return (
    <OrganizationForm
      mode="edit"
      initialValues={{
        name: organization.name,
        currency: organization.currency,
        country: organization.country,
        industry: organization.industry ?? undefined,
        ntn: organization.ntn ?? undefined,
        strn: organization.strn ?? undefined,
        cnic: organization.cnic ?? undefined,
        logo_url: organization.logo_url ?? undefined,
        fbr_enabled: organization.fbr_enabled,
        fbr_environment: organization.fbr_environment,
        fbr_province: organization.fbr_province ?? undefined,
        address_attention: organization.address?.attention ?? undefined,
        address_line1: organization.address?.line1 ?? undefined,
        address_line2: organization.address?.line2 ?? undefined,
        address_city: organization.address?.city ?? undefined,
        address_state: organization.address?.state ?? undefined,
        address_country: organization.address?.country ?? undefined,
        address_postal_code: organization.address?.postal_code ?? undefined,
        address_phone: organization.address?.phone ?? undefined,
        fiscal_year_start_month: organization.fiscal_year_start_month,
        is_active: organization.is_active,
      }}
      submitting={update.isPending}
      sandboxConfigured={organization.fbr_sandbox_configured}
      productionConfigured={organization.fbr_production_configured}
      organizationId={organization.id}
      onCancel={() => router.push(`/organizations/${organization.id}`)}
      onSubmit={submit}
    />
  );
}
