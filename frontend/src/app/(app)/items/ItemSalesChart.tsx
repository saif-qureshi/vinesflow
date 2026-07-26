"use client";

import { useState } from "react";
import { Segmented } from "antd";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useCurrency } from "@/hooks/useCurrency";
import { useItemSales } from "@/hooks/useProducts";
import { useAppTheme } from "@/hooks/useSession";

const AXIS = { tickLine: false, axisLine: false, tickMargin: 8, fontSize: 12, stroke: "#94a3b8" } as const;

type Period = "month" | "quarter" | "year";

export function ItemSalesChart({ productId }: { productId: number }) {
  const { money, compact } = useCurrency();
  const { accent } = useAppTheme();
  const [period, setPeriod] = useState<Period>("year");
  const { data: points } = useItemSales(productId, period);

  const data = (points ?? []).map((p) => ({ label: p.label, sales: Number(p.sales) }));
  const hasSales = data.some((d) => d.sales > 0);

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Segmented<Period>
          value={period}
          onChange={setPeriod}
          options={[
            { label: "This Month", value: "month" },
            { label: "This Quarter", value: "quarter" },
            { label: "This Year", value: "year" },
          ]}
        />
      </div>
      <div className="relative">
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={data} margin={{ left: 4, right: 8, top: 8 }}>
            <defs>
              <linearGradient id="fillItemSales" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={accent} stopOpacity={0.25} />
                <stop offset="100%" stopColor={accent} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="label" {...AXIS} />
            <YAxis {...AXIS} width={52} tickFormatter={(v: number) => compact(v)} />
            <Tooltip formatter={(v) => money(Number(v))} />
            <Area type="monotone" dataKey="sales" name="Sales" stroke={accent} strokeWidth={2} fill="url(#fillItemSales)" />
          </AreaChart>
        </ResponsiveContainer>
        {!hasSales && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <span className="text-sm text-gray-400">No sales recorded for this item yet</span>
          </div>
        )}
      </div>
    </div>
  );
}
