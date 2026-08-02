"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowDownLeft,
  ArrowUpRight,
  BarChart3,
  ChevronRight,
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

const CATEGORY: Record<string, { icon: LucideIcon; tint: string; rank: number }> = {
  Financial: { icon: Landmark, tint: "text-violet-600 bg-violet-50", rank: 0 },
  Receivables: { icon: ArrowDownLeft, tint: "text-emerald-600 bg-emerald-50", rank: 1 },
  Payables: { icon: ArrowUpRight, tint: "text-rose-600 bg-rose-50", rank: 2 },
  Sales: { icon: ShoppingCart, tint: "text-blue-600 bg-blue-50", rank: 3 },
  "Purchases and Expenses": { icon: ShoppingBag, tint: "text-teal-600 bg-teal-50", rank: 4 },
  Inventory: { icon: Warehouse, tint: "text-amber-600 bg-amber-50", rank: 5 },
};

function meta(category: string) {
  return CATEGORY[category] ?? { icon: BarChart3, tint: "text-slate-600 bg-slate-100", rank: 99 };
}

export default function ReportsPage() {
  const router = useRouter();
  const list = useReportList();
  const [q, setQ] = useState("");
  const [active, setActive] = useState<string | null>(null);

  const categories = useMemo(() => {
    const map = new Map<string, ReportListItem[]>();
    for (const r of list.data ?? []) {
      const arr = map.get(r.category) ?? [];
      arr.push(r);
      map.set(r.category, arr);
    }
    return [...map.entries()].sort((a, b) => meta(a[0]).rank - meta(b[0]).rank);
  }, [list.data]);

  const term = q.trim().toLowerCase();
  const activeCategory = active ?? categories[0]?.[0] ?? null;

  const visible = useMemo(() => {
    if (term) {
      return (list.data ?? []).filter(
        (r) =>
          r.name.toLowerCase().includes(term) || r.description?.toLowerCase().includes(term),
      );
    }
    return categories.find(([c]) => c === activeCategory)?.[1] ?? [];
  }, [term, list.data, categories, activeCategory]);

  return (
    <div className="space-y-4">
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
        <div className="flex flex-col gap-4 lg:flex-row">
          <nav className="shrink-0 lg:w-60">
            <div className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0">
              {categories.map(([category, reports]) => {
                const { icon: Icon, tint } = meta(category);
                const isActive = !term && category === activeCategory;
                return (
                  <button
                    key={category}
                    onClick={() => {
                      setActive(category);
                      setQ("");
                    }}
                    className={`flex items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2.5 text-sm transition lg:w-full ${
                      isActive
                        ? "bg-white font-medium text-slate-900 shadow-sm ring-1 ring-gray-200"
                        : "text-slate-500 hover:bg-white/70 hover:text-slate-800"
                    }`}
                  >
                    <span className={`grid h-7 w-7 place-items-center rounded-md ${tint}`}>
                      <Icon size={15} />
                    </span>
                    <span className="flex-1 text-left">{category}</span>
                    <span className="text-xs text-gray-400">{reports.length}</span>
                  </button>
                );
              })}
            </div>
          </nav>

          <div className="min-w-0 flex-1 rounded-xl border border-gray-200 bg-white">
            {term && (
              <div className="border-b border-gray-100 px-5 py-2.5 text-xs text-gray-400">
                {visible.length} {visible.length === 1 ? "result" : "results"} for “{q}”
              </div>
            )}
            <ul className="divide-y divide-gray-100">
              {visible.map((r) => {
                const { icon: Icon, tint } = meta(r.category);
                return (
                  <li key={r.key}>
                    <button
                      onClick={() => router.push(`/reports/${r.key}`)}
                      className="group flex w-full items-center gap-3 px-5 py-3.5 text-left transition hover:bg-slate-50"
                    >
                      <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg ${tint}`}>
                        <Icon size={16} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block font-medium text-slate-800 group-hover:text-slate-900">
                          {r.name}
                        </span>
                        {r.description && (
                          <span className="mt-0.5 block truncate text-xs text-gray-400">
                            {r.description}
                          </span>
                        )}
                      </span>
                      {term && (
                        <span className="hidden shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500 sm:inline">
                          {r.category}
                        </span>
                      )}
                      <ChevronRight
                        size={16}
                        className="shrink-0 text-gray-300 transition group-hover:translate-x-0.5 group-hover:text-slate-500"
                      />
                    </button>
                  </li>
                );
              })}
            </ul>
            {visible.length === 0 && (
              <div className="p-10 text-center text-sm text-gray-400">
                No reports match “{q}”.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
