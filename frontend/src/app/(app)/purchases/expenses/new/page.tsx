"use client";

import { useRouter } from "next/navigation";
import dayjs from "dayjs";

import { App, PageHeader } from "@/components/ui";
import { useCreateExpense } from "@/hooks/useExpenses";
import { apiErrorMessage } from "@/lib/api";
import { ExpenseForm, type ExpenseFormValues } from "../ExpenseForm";

export default function NewExpensePage() {
  const router = useRouter();
  const { message } = App.useApp();
  const create = useCreateExpense();

  const submit = async (values: ExpenseFormValues) => {
    try {
      const rec = await create.mutateAsync({
        expense_date: values.expense_date.format("YYYY-MM-DD"),
        paid_through_account_id: values.paid_through_account_id!,
        vendor_id: values.vendor_id ?? null,
        tax_amount: Number(values.tax_amount || 0),
        reference_no: values.reference_no || null,
        notes: values.notes || null,
        lines: (values.lines ?? []).map((l) => ({
          account_id: l.account_id!,
          description: l.description || null,
          amount: Number(l.amount || 0),
        })),
      });
      message.success("Expense saved as draft");
      router.push(`/purchases/expenses/${rec.id}`);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader title="New Expense" onBack={() => router.push("/purchases/expenses")} />
      <ExpenseForm
        initialValues={{ expense_date: dayjs(), lines: [{}] }}
        submitLabel="Save as draft"
        pending={create.isPending}
        onSubmit={submit}
        onCancel={() => router.push("/purchases/expenses")}
      />
    </div>
  );
}
