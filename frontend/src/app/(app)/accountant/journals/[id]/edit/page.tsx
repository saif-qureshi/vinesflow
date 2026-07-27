"use client";

import { useParams, useRouter } from "next/navigation";
import dayjs from "dayjs";

import { App, Button, Card, PageHeader, Spin } from "@/components/ui";
import { useUpdateVoucher, useVoucher } from "@/hooks/useAccounting";
import { apiErrorMessage } from "@/lib/api";
import { JournalForm, type JournalFormValues } from "../../JournalForm";

export default function EditJournalPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { message } = App.useApp();
  const { data: voucher, isLoading } = useVoucher(Number(id));
  const update = useUpdateVoucher();

  const back = () => router.push(`/accountant/journals/${id}`);

  if (isLoading || !voucher) {
    return (
      <div className="flex justify-center p-12">
        <Spin />
      </div>
    );
  }

  if (voucher.status !== "draft") {
    return (
      <div className="space-y-4">
        <PageHeader title={voucher.number} onBack={back} />
        <Card>
          <p className="text-gray-500">Only draft vouchers can be edited.</p>
          <Button className="mt-3" onClick={back}>
            Back to voucher
          </Button>
        </Card>
      </div>
    );
  }

  const initialValues: JournalFormValues = {
    date: dayjs(voucher.posting_date),
    reference_no: voucher.reference_no ?? undefined,
    description: voucher.description ?? undefined,
    lines: voucher.lines.map((l) => ({
      account_id: l.account_id,
      debit: Number(l.debit) || undefined,
      credit: Number(l.credit) || undefined,
      description: l.description ?? undefined,
    })),
  };

  const submit = async (values: JournalFormValues) => {
    try {
      await update.mutateAsync({
        id: voucher.id,
        payload: {
          date: values.date.format("YYYY-MM-DD"),
          reference_no: values.reference_no || null,
          description: values.description || null,
          lines: values.lines.map((l) => ({
            account_id: l.account_id!,
            debit: Number(l.debit || 0),
            credit: Number(l.credit || 0),
            description: l.description || null,
          })),
        },
      });
      message.success("Draft updated");
      back();
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader title={`Edit ${voucher.number}`} onBack={back} />
      <JournalForm
        initialValues={initialValues}
        submitLabel="Save draft"
        pending={update.isPending}
        onSubmit={submit}
        onCancel={back}
      />
    </div>
  );
}
