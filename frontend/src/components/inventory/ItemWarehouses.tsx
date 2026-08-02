"use client";

import type { ColumnsType } from "antd/es/table";

import { Table } from "@/components/ui";
import type { Bin, ItemStock, Warehouse } from "@/types";

const num = (s: string) => {
  const n = Number(s);
  return Number.isNaN(n) ? s : String(n);
};

interface Row {
  key: string;
  location_id: number;
  bin_id: number | null;
  quantity: string;
}

export function ItemWarehouses({
  stock,
  warehouses,
  bins,
}: {
  stock?: ItemStock;
  warehouses: Warehouse[];
  bins: Bin[];
}) {
  const whName = (id: number) => warehouses.find((w) => w.id === id)?.name ?? `#${id}`;
  const binName = (id: number | null) => {
    if (id == null) return "Unassigned";
    const bin = bins.find((row) => row.id === id);
    return bin ? `${bin.code} · ${bin.name}` : `#${id}`;
  };

  const rows: Row[] = (stock?.by_bin ?? []).map((row) => ({
    ...row,
    key: `${row.location_id}:${row.bin_id ?? "unassigned"}`,
  }));

  const columns: ColumnsType<Row> = [
    { title: "Warehouse", key: "wh", render: (_, r) => whName(r.location_id) },
    { title: "Bin", key: "bin", render: (_, r) => binName(r.bin_id) },
    {
      title: "Stock on hand",
      key: "qty",
      align: "right",
      render: (_, r) => <span className="font-medium tabular-nums">{num(r.quantity)}</span>,
    },
  ];

  return (
    <div className="overflow-hidden rounded-xl border border-gray-100 bg-white">
      <Table<Row>
        rowKey="key"
        columns={columns}
        dataSource={rows}
        pagination={false}
      />
    </div>
  );
}
