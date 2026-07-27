"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowDownLeft,
  ArrowUpRight,
  BarChart3,
  Landmark,
  Search,
  ShoppingBag,
  ShoppingCart,
  Warehouse,
  type LucideIcon,
} from "lucide-react";

import { Input, PageHeader, Spin } from "@/components/ui";
import { useReportList } from "@/hooks/useReports";
import type { ReportListItem } from "@/types/report";

const CATEGORY: Record<string, { icon: LucideIcon; tint: string }> = {
  Financial: { icon: Landmark, tint: "text-violet-600 bg-violet-50" },
  Receivables: { icon: ArrowDownLeft, tint: "text-emerald-600 bg-emerald-50" },
  Payables: { icon: ArrowUpRight, tint: "text-rose-600 bg-rose-50" },
  Sales: { icon: ShoppingCart, tint: "text-blue-600 bg-blue-50" },
  Inventory: { icon: Warehouse, tint: "text-amber-600 bg-amber-50" },
  "Purchases and Expenses": { icon: ShoppingBag, tint: "text-teal-600 bg-teal-50" },
};

function meta(category: string) {
  return CATEGORY[category] ?? { icon: BarChart3, tint: "text-slate-600 bg-slate-100" };
}

export default function ReportsPage() {
  const router = useRouter();
  const list = useReportList();
  const [q, setQ] = useState("");

  const grouped = useMemo(() => {
    const term = q.trim().toLowerCase();
    const filtered = (list.data ?? []).filter(
      (r) => !term || r.name.toLowerCase().includes(term) || r.category.toLowerCase().includes(term),
    );
    const map = new Map<string, ReportListItem[]>();
    for (const r of filtered) {
      const arr = map.get(r.category) ?? [];
      arr.push(r);
      map.set(r.category, arr);
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [list.data, q]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        description="Run, filter and export your business and financial reports."
        actions={
          <Input
            prefix={<Search size={15} className="text-gray-400" />}
            placeholder="Search reports"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="w-64"
            allowClear
          />
        }
      />

      {list.isLoading ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <Spin />
        </div>
      ) : (
        <div className="space-y-8">
          {grouped.map(([category, reports]) => {
            const { icon: Icon, tint } = meta(category);
            return (
              <section key={category}>
                <div className="mb-3 flex items-center gap-2">
                  <span className={`grid h-7 w-7 place-items-center rounded-lg ${tint}`}>
                    <Icon size={15} />
                  </span>
                  <h2 className="text-sm font-semibold text-slate-700">{category}</h2>
                  <span className="text-xs text-gray-400">{reports.length}</span>
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  {reports.map((r) => (
                    <button
                      key={r.key}
                      onClick={() => router.push(`/reports/${r.key}`)}
                      className="group rounded-xl border border-gray-200 bg-white p-4 text-left transition hover:border-violet-300 hover:shadow-sm"
                    >
                      <div className="font-medium text-slate-800 group-hover:text-violet-700">
                        {r.name}
                      </div>
                      {r.description && (
                        <div className="mt-1 text-xs leading-relaxed text-gray-400">
                          {r.description}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </section>
            );
          })}
          {grouped.length === 0 && (
            <div className="flex min-h-[30vh] items-center justify-center text-gray-400">
              No reports match “{q}”.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
