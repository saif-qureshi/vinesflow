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
    try {
      await update.mutateAsync({
        name: values.name,
        currency: values.currency,
        country: values.country,
        industry: values.industry,
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
        fiscal_year_start_month: organization.fiscal_year_start_month,
        is_active: organization.is_active,
      }}
      submitting={update.isPending}
      onCancel={() => router.push(`/organizations/${organization.id}`)}
      onSubmit={submit}
    />
  );
}
