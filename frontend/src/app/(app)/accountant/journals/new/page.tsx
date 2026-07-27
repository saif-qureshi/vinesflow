"use client";

import { useRouter } from "next/navigation";
import dayjs from "dayjs";

import { App, PageHeader } from "@/components/ui";
import { useCreateVoucher } from "@/hooks/useAccounting";
import { apiErrorMessage } from "@/lib/api";
import { JournalForm, type JournalFormValues } from "../JournalForm";

export default function NewJournalPage() {
  const router = useRouter();
  const { message } = App.useApp();
  const create = useCreateVoucher();

  const submit = async (values: JournalFormValues) => {
    try {
      const res = await create.mutateAsync({
        date: values.date.format("YYYY-MM-DD"),
        reference_no: values.reference_no || null,
        description: values.description || null,
        lines: values.lines.map((l) => ({
          account_id: l.account_id!,
          debit: Number(l.debit || 0),
          credit: Number(l.credit || 0),
          description: l.description || null,
        })),
      });
      message.success(`Draft ${res.data.number} saved`);
      router.push(`/accountant/journals/${res.data.id}`);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader
        title="New Journal"
        description="A manual double-entry adjustment"
        onBack={() => router.push("/accountant/journals")}
      />
      <JournalForm
        initialValues={{ date: dayjs(), lines: [{}, {}] }}
        submitLabel="Save as draft"
        pending={create.isPending}
        onSubmit={submit}
        onCancel={() => router.push("/accountant/journals")}
      />
    </div>
  );
}
