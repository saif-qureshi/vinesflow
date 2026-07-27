"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import dayjs from "dayjs";

import { App, Card, PageHeader, Spin } from "@/components/ui";
import { useExpense, useUpdateExpense } from "@/hooks/useExpenses";
import { apiErrorMessage } from "@/lib/api";
import { ExpenseForm, type ExpenseFormValues } from "../../ExpenseForm";

export default function EditExpensePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const expenseId = Number(id);
  const router = useRouter();
  const { message } = App.useApp();
  const expense = useExpense(expenseId);
  const update = useUpdateExpense(expenseId);
  const back = () => router.push(`/purchases/expenses/${expenseId}`);

  const submit = async (values: ExpenseFormValues) => {
    try {
      await update.mutateAsync({
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
      message.success("Expense updated");
      back();
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  if (expense.isLoading || !expense.data) {
    return (
      <Card>
        <Spin />
      </Card>
    );
  }
  if (expense.data.status !== "draft") {
    router.replace(`/purchases/expenses/${expenseId}`);
    return null;
  }

  const e = expense.data;
  const initialValues: ExpenseFormValues = {
    expense_date: dayjs(e.expense_date),
    paid_through_account_id: e.paid_through_account_id,
    vendor_id: e.vendor_id ?? undefined,
    reference_no: e.reference_no ?? undefined,
    tax_amount: Number(e.tax_amount),
    notes: e.notes ?? undefined,
    lines: e.lines.map((l) => ({
      account_id: l.account_id,
      description: l.description ?? undefined,
      amount: Number(l.amount),
    })),
  };

  return (
    <div className="space-y-4">
      <PageHeader title={`Edit ${e.number}`} onBack={back} />
      <ExpenseForm
        initialValues={initialValues}
        submitLabel="Save changes"
        pending={update.isPending}
        onSubmit={submit}
        onCancel={back}
      />
    </div>
  );
}
