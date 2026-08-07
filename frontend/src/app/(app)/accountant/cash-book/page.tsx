"use client";

import { Fragment, useState } from "react";
import { DatePicker } from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp } from "lucide-react";

import { Button, Card, PageHeader, Spin } from "@/components/ui";
import { useCurrency } from "@/hooks/useCurrency";
import { useRunReport } from "@/hooks/useReports";
import type { ReportRow } from "@/types/report";

function num(value: unknown): number {
  return Number(value ?? 0);
}

function Amount({ value, bold }: { value: number; bold?: boolean }) {
  const { money } = useCurrency();
  const tone = value < 0 ? "text-red-600" : "text-slate-800";
  return (
    <span className={`tabular-nums ${tone} ${bold ? "font-semibold" : ""}`}>{money(value)}</span>
  );
}

function DayEntries({ accountId, day }: { accountId: number; day: string }) {
  const { money } = useCurrency();
  const statement = useRunReport("account_statement", {
    account_id: accountId,
    range: "custom",
    from: day,
    to: day,
  });
  const rows = (statement.data?.sections ?? []).flatMap((s) => s.rows).filter((r) => r.date);

  if (statement.isPending) {
    return (
      <div className="py-4 text-center">
        <Spin size="small" />
      </div>
    );
  }
  if (!rows.length) {
    return <p className="py-3 text-sm text-gray-400">No movement on this day.</p>;
  }
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-xs text-gray-400">
          <th className="pb-2 text-left font-normal">Voucher</th>
          <th className="pb-2 text-left font-normal">Details</th>
          <th className="w-32 pb-2 text-right font-normal">Received</th>
          <th className="w-32 pb-2 text-right font-normal">Paid</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row: ReportRow, i) => (
          <tr key={i} className="border-t border-gray-100">
            <td className="py-1.5 font-mono text-xs text-slate-500">{String(row.number ?? "")}</td>
            <td className="py-1.5">{String(row.description ?? "")}</td>
            <td className="py-1.5 text-right tabular-nums">
              {num(row.debit) ? money(num(row.debit)) : ""}
            </td>
            <td className="py-1.5 text-right tabular-nums">
              {num(row.credit) ? money(num(row.credit)) : ""}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function CashBookPage() {
  const [day, setDay] = useState<Dayjs>(dayjs());
  const [open, setOpen] = useState<string | null>(null);
  const iso = day.format("YYYY-MM-DD");
  const report = useRunReport("cash_book", { range: "custom", from: iso, to: iso });

  const accounts = (report.data?.sections ?? []).filter((s) => s.title);
  const totals = accounts.reduce(
    (acc, s) => ({
      opening: acc.opening + num(s.subtotal?.opening),
      received: acc.received + num(s.subtotal?.received),
      paid: acc.paid + num(s.subtotal?.paid),
      closing: acc.closing + num(s.subtotal?.closing),
    }),
    { opening: 0, received: 0, paid: 0, closing: 0 },
  );

  return (
    <div className="space-y-4">
      <PageHeader
        title="Cash &amp; Bank Book"
        description="What each account opened with, what moved, and what it closed with."
        actions={
          <div className="flex items-center gap-2">
            <Button icon={<ChevronLeft size={16} />} onClick={() => setDay(day.subtract(1, "day"))} />
            <DatePicker
              value={day}
              onChange={(d) => d && setDay(d)}
              format="DD MMM YYYY"
              allowClear={false}
            />
            <Button
              icon={<ChevronRight size={16} />}
              disabled={day.isSame(dayjs(), "day")}
              onClick={() => setDay(day.add(1, "day"))}
            />
          </div>
        }
      />

      <Card>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            ["Opening", totals.opening],
            ["Received", totals.received],
            ["Paid", totals.paid],
            ["Closing", totals.closing],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-lg bg-slate-50 p-3">
              <p className="text-xs text-gray-500">{label}</p>
              <p className="mt-1 text-lg">
                <Amount value={Number(value)} bold />
              </p>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        {report.isPending ? (
          <div className="py-10 text-center">
            <Spin />
          </div>
        ) : !accounts.length ? (
          <p className="py-6 text-center text-sm text-gray-400">
            No cash or bank accounts are configured yet.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-400">
                <th className="pb-2 text-left font-normal">Account</th>
                <th className="w-36 pb-2 text-right font-normal">Opening</th>
                <th className="w-36 pb-2 text-right font-normal">Received</th>
                <th className="w-36 pb-2 text-right font-normal">Paid</th>
                <th className="w-36 pb-2 text-right font-normal">Closing</th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody>
              {accounts.map((section) => {
                const title = section.title ?? "";
                const [code, ...rest] = title.split(" — ");
                const expanded = open === title;
                const accountId = num(section.rows.find((r) => r.account_id)?.account_id);
                const moved = num(section.subtotal?.received) || num(section.subtotal?.paid);
                return (
                  <Fragment key={title}>
                    <tr className="border-t border-gray-100">
                      <td className="py-2">
                        <span className="mr-2 font-mono text-slate-400">{code}</span>
                        {rest.join(" — ")}
                      </td>
                      <td className="py-2 text-right">
                        <Amount value={num(section.subtotal?.opening)} />
                      </td>
                      <td className="py-2 text-right">
                        <Amount value={num(section.subtotal?.received)} />
                      </td>
                      <td className="py-2 text-right">
                        <Amount value={num(section.subtotal?.paid)} />
                      </td>
                      <td className="py-2 text-right">
                        <Amount value={num(section.subtotal?.closing)} bold />
                      </td>
                      <td className="py-2 text-right">
                        {moved ? (
                          <button
                            type="button"
                            aria-label={expanded ? "Hide entries" : "Show entries"}
                            className="text-gray-400 hover:text-gray-600"
                            onClick={() => setOpen(expanded ? null : title)}
                          >
                            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                          </button>
                        ) : null}
                      </td>
                    </tr>
                    {expanded && accountId ? (
                      <tr>
                        <td colSpan={6} className="bg-slate-50 px-4 py-2">
                          <DayEntries accountId={accountId} day={iso} />
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
