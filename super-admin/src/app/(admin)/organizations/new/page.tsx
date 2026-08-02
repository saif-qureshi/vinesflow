"use client";

import { App } from "antd";
import { useRouter } from "next/navigation";

import {
  OrganizationForm,
  type OrganizationFormValues,
} from "@/components/OrganizationForm";
import { useOnboardOrganization } from "@/hooks/useSuperAdmin";
import { apiErrorMessage } from "@/lib/api";

export default function NewOrganizationPage() {
  const onboard = useOnboardOrganization();
  const router = useRouter();
  const { message } = App.useApp();

  const submit = async (values: OrganizationFormValues) => {
    try {
      const organization = await onboard.mutateAsync({
        name: values.name,
        currency: values.currency,
        country: values.country,
        industry: values.industry,
        fiscal_year_start_month: values.fiscal_year_start_month,
        owner_full_name: values.owner_full_name,
        owner_email: values.owner_email!,
        owner_password: values.owner_password!,
      });
      message.success("Organization created");
      router.replace(`/organizations/${organization.id}`);
    } catch (error) {
      message.error(apiErrorMessage(error, "Could not create organization"));
    }
  };

  return (
    <OrganizationForm
      mode="create"
      submitting={onboard.isPending}
      onCancel={() => router.push("/organizations")}
      onSubmit={submit}
    />
  );
}
