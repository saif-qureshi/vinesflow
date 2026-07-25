"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useCurrency } from "@/hooks/useCurrency";
import { useAppTheme } from "@/hooks/useSession";

const STATUS_COLOR: Record<string, string> = { Paid: "#16a34a", Pending: "#f59e0b", Overdue: "#dc2626" };
const AXIS = { tickLine: false, axisLine: false, tickMargin: 8, fontSize: 12, stroke: "#94a3b8" } as const;

export function RevenueChart({ data }: { data: { month: string; revenue: number }[] }) {
  const { money, compact } = useCurrency();
  const { accent } = useAppTheme();
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data} margin={{ left: 4, right: 8, top: 8 }}>
        <defs>
          <linearGradient id="fillRevenue" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity={0.25} />
            <stop offset="100%" stopColor={accent} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="month" {...AXIS} />
        <YAxis {...AXIS} width={52} tickFormatter={(v: number) => compact(v)} />
        <Tooltip formatter={(v) => money(Number(v))} />
        <Area type="monotone" dataKey="revenue" name="Revenue" stroke={accent} strokeWidth={2} fill="url(#fillRevenue)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function AgingChart({ data }: { data: { bucket: string; amount: number }[] }) {
  const { money, compact } = useCurrency();
  const { accent } = useAppTheme();
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ left: 4, right: 8, top: 8 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="bucket" {...AXIS} />
        <YAxis {...AXIS} width={52} tickFormatter={(v: number) => compact(v)} />
        <Tooltip formatter={(v) => money(Number(v))} cursor={{ fill: "#f8fafc" }} />
        <Bar dataKey="amount" name="Outstanding" fill={accent} radius={[4, 4, 0, 0]} maxBarSize={64} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function StatusChart({ data }: { data: { status: string; invoices: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Tooltip />
        <Pie data={data} dataKey="invoices" nameKey="status" innerRadius={56} outerRadius={86} paddingAngle={2} strokeWidth={2}>
          {data.map((entry) => (
            <Cell key={entry.status} fill={STATUS_COLOR[entry.status] ?? "#94a3b8"} />
          ))}
        </Pie>
        <Legend iconType="circle" />
      </PieChart>
    </ResponsiveContainer>
  );
}
