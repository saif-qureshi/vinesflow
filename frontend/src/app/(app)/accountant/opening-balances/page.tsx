"use client";

import { useState } from "react";
import { DatePicker, InputNumber } from "antd";
import dayjs, { type Dayjs } from "dayjs";

import { App, Button, Card, PageHeader, Tag } from "@/components/ui";
import {
  useAccounts,
  useCreateOpeningBalances,
  useVoucher,
  useVouchers,
} from "@/hooks/useAccounting";
import { useCurrency } from "@/hooks/useCurrency";
import { useSettingsGroup } from "@/hooks/useSettings";
import { apiErrorMessage } from "@/lib/api";

const BALANCE_SHEET = new Set(["asset", "liability", "equity"]);

const DERIVED_ROLES = [
  "inventory",
  "accounts_receivable",
  "accounts_payable",
  "opening_balance_equity",
] as const;

export default function OpeningBalancesPage() {
  const { message } = App.useApp();
  const { money } = useCurrency();
  const accounts = useAccounts();
  const vouchers = useVouchers();
  const config = useSettingsGroup<Record<string, string>>("accounting");
  const create = useCreateOpeningBalances();
  const [date, setDate] = useState<Dayjs>(dayjs());
  const [amounts, setAmounts] = useState<Record<number, { debit?: number; credit?: number }>>({});

  const posted = (vouchers.data ?? []).find(
    (voucher) =>
      voucher.voucher_type === "opening" &&
      voucher.status === "posted" &&
      (voucher.source_type == null || voucher.source_type === "opening_balances"),
  );
  const detail = useVoucher(posted?.id ?? null);

  const byId = new Map((accounts.data ?? []).map((a) => [a.id, a]));
  const derived = new Set(
    DERIVED_ROLES.map((role) => Number(config.data?.[role])).filter((id) => !Number.isNaN(id)),
  );
  const rows = (accounts.data ?? []).filter(
    (a) => a.is_postable && BALANCE_SHEET.has(a.account_type) && !derived.has(a.id),
  );

  const totalDebit = rows.reduce((s, a) => s + Number(amounts[a.id]?.debit || 0), 0);
  const totalCredit = rows.reduce((s, a) => s + Number(amounts[a.id]?.credit || 0), 0);
  const diff = Math.round((totalDebit - totalCredit) * 100) / 100;

  const set = (id: number, key: "debit" | "credit", val: number | null) =>
    setAmounts((m) => ({ ...m, [id]: { ...m[id], [key]: val ?? 0 } }));

  const save = async () => {
    const entries = rows
      .map((a) => ({
        account_id: a.id,
        debit: Number(amounts[a.id]?.debit || 0),
        credit: Number(amounts[a.id]?.credit || 0),
      }))
      .filter((e) => e.debit || e.credit);
    if (!entries.length) {
      message.warning("Enter at least one balance");
      return;
    }
    try {
      await create.mutateAsync({ date: date.format("YYYY-MM-DD"), entries });
      message.success("Opening balances posted");
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const label = (accountId: number) => {
    const account = byId.get(accountId);
    return account ? { code: account.code, name: account.name } : { code: "", name: "—" };
  };

  if (posted) {
    const lines = detail.data?.lines ?? [];
    const debit = lines.reduce((s, l) => s + Number(l.debit), 0);
    const credit = lines.reduce((s, l) => s + Number(l.credit), 0);
    return (
      <div className="space-y-4">
        <PageHeader
          title="Opening Balances"
          description={`Your starting position as of ${dayjs(posted.posting_date).format("DD MMM YYYY")}`}
          actions={<Tag color="green">{posted.number}</Tag>}
        />
        <Card>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-400">
                <th className="pb-2 text-left font-normal">Account</th>
                <th className="w-40 pb-2 text-right font-normal">Debit</th>
                <th className="w-40 pb-2 text-right font-normal">Credit</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line) => {
                const account = label(line.account_id);
                return (
                  <tr key={line.id} className="border-t border-gray-100">
                    <td className="py-1.5">
                      <span className="mr-2 font-mono text-slate-400">{account.code}</span>
                      {account.name}
                    </td>
                    <td className="py-1.5 text-right tabular-nums">
                      {Number(line.debit) ? money(Number(line.debit)) : ""}
                    </td>
                    <td className="py-1.5 text-right tabular-nums">
                      {Number(line.credit) ? money(Number(line.credit)) : ""}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <div className="mt-4 flex items-center justify-between rounded-lg bg-slate-50 p-3 text-sm">
            <div className="flex gap-6 text-gray-500">
              <span>
                Debit <b className="tabular-nums text-slate-800">{money(debit)}</b>
              </span>
              <span>
                Credit <b className="tabular-nums text-slate-800">{money(credit)}</b>
              </span>
            </div>
            <span className="text-gray-500">
              Stock and party balances come from item opening stock and your unsettled documents,
              so they are not listed here.
            </span>
          </div>

          <p className="mt-4 text-sm text-gray-500">
            To change these, reverse {posted.number} from Vouchers and enter them again.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Opening Balances"
        description="Enter each account's balance as of your start date. Any difference posts to Opening Balance Equity."
        actions={
          <DatePicker
            value={date}
            onChange={(d) => d && setDate(d)}
            format="DD MMM YYYY"
            allowClear={false}
          />
        }
      />
      <Card>
        <p className="mb-4 text-sm text-gray-500">
          Stock comes from item opening stock, and what customers owe you or you owe suppliers
          comes from entering those unpaid invoices and bills. Those accounts are excluded here so
          the balance sheet never holds a figure no item or party can account for.
        </p>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-400">
              <th className="pb-2 text-left font-normal">Account</th>
              <th className="w-40 pb-2 text-right font-normal">Debit</th>
              <th className="w-40 pb-2 text-right font-normal">Credit</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id} className="border-t border-gray-100">
                <td className="py-1.5">
                  <span className="mr-2 font-mono text-slate-400">{a.code}</span>
                  {a.name}
                </td>
                <td className="py-1.5">
                  <InputNumber
                    className="!w-full"
                    min={0}
                    controls={false}
                    value={amounts[a.id]?.debit}
                    onChange={(v) => set(a.id, "debit", v)}
                  />
                </td>
                <td className="py-1.5">
                  <InputNumber
                    className="!w-full"
                    min={0}
                    controls={false}
                    value={amounts[a.id]?.credit}
                    onChange={(v) => set(a.id, "credit", v)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="mt-4 flex items-center justify-between rounded-lg bg-slate-50 p-3 text-sm">
          <div className="flex gap-6 text-gray-500">
            <span>
              Debit <b className="tabular-nums text-slate-800">{money(totalDebit)}</b>
            </span>
            <span>
              Credit <b className="tabular-nums text-slate-800">{money(totalCredit)}</b>
            </span>
          </div>
          {diff === 0 ? (
            <Tag color="green">Balanced</Tag>
          ) : (
            <Tag color="gold">{money(Math.abs(diff))} → Opening Balance Equity</Tag>
          )}
        </div>

        <div className="mt-4 flex justify-end">
          <Button type="primary" onClick={save} loading={create.isPending}>
            Save opening balances
          </Button>
        </div>
      </Card>
    </div>
  );
}
