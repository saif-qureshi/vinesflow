"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { Pencil } from "lucide-react";

import { App, Button, Card, PageHeader, Popconfirm, Spin, Tag } from "@/components/ui";
import { useAccounts } from "@/hooks/useAccounting";
import {
  useCancelExpense,
  useDeleteExpense,
  useExpense,
  useSubmitExpense,
} from "@/hooks/useExpenses";
import { useCurrency } from "@/hooks/useCurrency";
import { useCan } from "@/hooks/useSession";
import { apiErrorMessage } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { ExpenseStatus } from "@/types";

const STATUS_META: Record<ExpenseStatus, { color: string; label: string }> = {
  draft: { color: "gold", label: "Draft" },
  submitted: { color: "green", label: "Submitted" },
  cancelled: { color: "red", label: "Cancelled" },
};

export default function ExpenseDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const expenseId = Number(id);
  const router = useRouter();
  const can = useCan();
  const { money } = useCurrency();
  const { message } = App.useApp();
  const expense = useExpense(expenseId);
  const accounts = useAccounts();
  const submit = useSubmitExpense();
  const cancel = useCancelExpense();
  const del = useDeleteExpense();

  const accountLabel = (accountId: number) => {
    const a = (accounts.data ?? []).find((x) => x.id === accountId);
    return a ? `${a.code} — ${a.name}` : `#${accountId}`;
  };

  const run = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      message.success(ok);
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

  const e = expense.data;
  const meta = STATUS_META[e.status];
  const isDraft = e.status === "draft";
  const isSubmitted = e.status === "submitted";

  const actions = (
    <div className="flex items-center gap-2">
      {isDraft && can("expenses:update") && (
        <Button
          icon={<Pencil size={15} />}
          onClick={() => router.push(`/purchases/expenses/${e.id}/edit`)}
        >
          Edit
        </Button>
      )}
      {isDraft && can("expenses:delete") && (
        <Popconfirm
          title="Delete this draft expense?"
          onConfirm={() =>
            run(async () => {
              await del.mutateAsync(e.id);
              router.push("/purchases/expenses");
            }, "Expense deleted")
          }
        >
          <Button danger>Delete</Button>
        </Popconfirm>
      )}
      {isDraft && can("expenses:update") && (
        <Button
          type="primary"
          loading={submit.isPending}
          onClick={() => run(() => submit.mutateAsync(e.id), "Expense submitted — posted to the ledger")}
        >
          Submit
        </Button>
      )}
      {isSubmitted && can("expenses:update") && (
        <Popconfirm
          title="Cancel this expense? Its ledger entry will be reversed."
          onConfirm={() => run(() => cancel.mutateAsync(e.id), "Expense cancelled and reversed")}
        >
          <Button danger loading={cancel.isPending}>
            Cancel expense
          </Button>
        </Popconfirm>
      )}
    </div>
  );

  return (
    <div className="space-y-4">
      <PageHeader
        title={e.number}
        onBack={() => router.push("/purchases/expenses")}
        actions={actions}
      />

      <Card>
        <div className="mb-4 flex items-center gap-3">
          <Tag color={meta.color}>{meta.label}</Tag>
          <span className="text-2xl font-semibold tabular-nums text-slate-900">
            {money(Number(e.total))}
          </span>
        </div>

        <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm sm:grid-cols-4">
          <Field label="Date">{formatDate(e.expense_date)}</Field>
          <Field label="Paid through">{accountLabel(e.paid_through_account_id)}</Field>
          <Field label="Vendor">{e.vendor?.name ?? e.vendor_name ?? "—"}</Field>
          <Field label="Reference #">{e.reference_no ?? "—"}</Field>
        </dl>

        <table className="mt-6 w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-400">
              <th className="pb-2 text-left font-normal">Category</th>
              <th className="pb-2 text-left font-normal">Description</th>
              <th className="pb-2 text-right font-normal">Amount</th>
            </tr>
          </thead>
          <tbody>
            {e.lines.map((l) => (
              <tr key={l.id} className="border-t border-gray-100">
                <td className="py-2">{accountLabel(l.account_id)}</td>
                <td className="py-2 text-gray-500">{l.description ?? "—"}</td>
                <td className="py-2 text-right tabular-nums">{money(Number(l.amount))}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="mt-4 flex flex-col items-end gap-1 text-sm text-gray-500">
          <span>
            Subtotal <b className="ml-4 tabular-nums text-slate-800">{money(Number(e.subtotal))}</b>
          </span>
          <span>
            Input tax{" "}
            <b className="ml-4 tabular-nums text-slate-800">{money(Number(e.tax_amount))}</b>
          </span>
          <span className="text-slate-900">
            Total <b className="ml-4 tabular-nums">{money(Number(e.total))}</b>
          </span>
        </div>

        {e.notes && <p className="mt-4 text-sm text-gray-500">{e.notes}</p>}
      </Card>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-gray-400">{label}</dt>
      <dd className="mt-0.5 text-slate-800">{children}</dd>
    </div>
  );
}
