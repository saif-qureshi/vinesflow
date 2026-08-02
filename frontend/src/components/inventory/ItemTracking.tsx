"use client";

import dayjs from "dayjs";

import { Card, Table, Tag } from "@/components/ui";
import { useLots, useSerialUnits } from "@/hooks/useTracking";
import type { Bin, SerialUnit, StockLot, Warehouse } from "@/types";

function expiryTag(expiry: string | null) {
  if (!expiry) return <span className="text-gray-400">No expiry</span>;
  const date = dayjs(expiry);
  if (date.isBefore(dayjs(), "day")) return <Tag color="red">Expired · {date.format("DD MMM YYYY")}</Tag>;
  if (date.diff(dayjs(), "day") <= 30) {
    return <Tag color="orange">Expires {date.format("DD MMM YYYY")}</Tag>;
  }
  return date.format("DD MMM YYYY");
}

export function ItemTracking({
  productId,
  mode,
  warehouses,
  bins,
}: {
  productId: number;
  mode: "lot" | "serial";
  warehouses: Warehouse[];
  bins: Bin[];
}) {
  const lots = useLots(mode === "lot" ? productId : null);
  const serials = useSerialUnits(mode === "serial" ? productId : null);
  const warehouseName = (id: number | null) =>
    id == null ? "—" : warehouses.find((warehouse) => warehouse.id === id)?.name ?? `#${id}`;
  const binName = (id: number | null) => {
    if (id == null) return "Unassigned";
    const bin = bins.find((candidate) => candidate.id === id);
    return bin ? `${bin.code} — ${bin.name}` : `#${id}`;
  };

  if (mode === "lot") {
    return (
      <Card
        title="Batch / lot register"
        extra={<span className="text-xs text-gray-500">Outbound allocation follows earliest expiry first</span>}
        className="mt-2 border-gray-100"
      >
        <Table<StockLot>
          rowKey="id"
          loading={lots.isLoading}
          dataSource={lots.data ?? []}
          pagination={false}
          columns={[
            {
              title: "Lot number",
              dataIndex: "lot_number",
              render: (value: string) => <span className="font-medium text-slate-800">{value}</span>,
            },
            {
              title: "Manufactured",
              dataIndex: "manufactured_date",
              render: (value: string | null) => (value ? dayjs(value).format("DD MMM YYYY") : "—"),
            },
            { title: "Expiry", dataIndex: "expiry_date", render: expiryTag },
            {
              title: "On hand",
              dataIndex: "quantity",
              align: "right",
              render: (value: string) => <span className="font-medium tabular-nums">{Number(value)}</span>,
            },
            {
              title: "Status",
              key: "status",
              render: (_: unknown, lot: StockLot) =>
                lot.is_active ? <Tag>Active</Tag> : <Tag>Inactive</Tag>,
            },
          ]}
          locale={{ emptyText: "No batches or lots have been received yet" }}
        />
      </Card>
    );
  }

  return (
    <Card title="Serial number register" className="mt-2 border-gray-100">
      <Table<SerialUnit>
        rowKey="id"
        loading={serials.isLoading}
        dataSource={serials.data ?? []}
        pagination={{ pageSize: 25, hideOnSinglePage: true }}
        columns={[
          {
            title: "Serial number",
            dataIndex: "serial_number",
            render: (value: string) => <span className="font-medium text-slate-800">{value}</span>,
          },
          {
            title: "Status",
            dataIndex: "status",
            render: (value: string) => (
              <Tag color={value === "in_stock" ? "green" : undefined} className="capitalize">
                {value.replaceAll("_", " ")}
              </Tag>
            ),
          },
          {
            title: "Warehouse",
            dataIndex: "location_id",
            render: warehouseName,
          },
          { title: "Bin", dataIndex: "bin_id", render: binName },
        ]}
        locale={{ emptyText: "No serial numbers have been received yet" }}
      />
    </Card>
  );
}
