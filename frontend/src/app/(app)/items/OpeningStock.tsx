"use client";

import { useEffect, useMemo, useState } from "react";

import { Alert, InputNumber } from "@/components/ui";
import { useOpeningStock } from "@/hooks/useInventory";
import { useWarehouses } from "@/hooks/useWarehouses";

export interface OpeningEntry {
  location_id: number;
  quantity: number;
  unit_cost: number | null;
}

type Row = { qty: number | null; cost: number | null };

export function OpeningStock({
  productId,
  onChange,
}: {
  productId?: number;
  onChange: (entries: OpeningEntry[]) => void;
}) {
  const { data: warehouses } = useWarehouses();
  const { data: state } = useOpeningStock(productId);
  const locked = state?.locked ?? false;

  const [rows, setRows] = useState<Record<number, Row>>({});

  useEffect(() => {
    if (!state) return;
    const init: Record<number, Row> = {};
    for (const e of state.entries) {
      const q = Number(e.quantity);
      init[e.location_id] = {
        qty: q > 0 ? q : null,
        cost: e.unit_cost != null ? Number(e.unit_cost) : null,
      };
    }
    setRows(init);
  }, [state]);

  const activeWarehouses = useMemo(
    () => (warehouses ?? []).filter((w) => w.is_active),
    [warehouses],
  );

  const emit = (next: Record<number, Row>) => {
    onChange(
      Object.entries(next)
        .filter(([, v]) => v.qty != null)
        .map(([lid, v]) => ({
          location_id: Number(lid),
          quantity: v.qty as number,
          unit_cost: v.cost ?? null,
        })),
    );
  };

  const update = (locationId: number, field: keyof Row, value: number | null) => {
    setRows((prev) => {
      const next = {
        ...prev,
        [locationId]: { qty: prev[locationId]?.qty ?? null, cost: prev[locationId]?.cost ?? null, [field]: value },
      };
      emit(next);
      return next;
    });
  };

  if (!activeWarehouses.length) return null;

  return (
    <div className="mt-4 border-t border-gray-100 pt-4">
      <div className="mb-1 text-sm font-medium text-gray-700">Opening Stock</div>
      <div className="mb-3 text-xs text-gray-400">
        Quantity on hand when you start using Vineflow. Rate is optional (captured for future
        valuation). Editable until this item&apos;s first transaction.
      </div>
      {locked && (
        <Alert
          type="info"
          showIcon
          title="Opening stock is locked because this item already has transactions. Use Adjust Stock to change quantities."
          className="!mb-3"
        />
      )}
      <div className="space-y-2">
        {activeWarehouses.map((w) => (
          <div key={w.id} className="grid grid-cols-[1fr_7rem_10rem] items-center gap-3">
            <span className="truncate text-sm text-gray-600">{w.name}</span>
            <InputNumber
              min={0}
              placeholder="Qty"
              disabled={locked}
              value={rows[w.id]?.qty ?? undefined}
              onChange={(v) => update(w.id, "qty", v as number | null)}
              className="!w-full"
            />
            <InputNumber
              min={0}
              placeholder="Rate / unit"
              prefix="Rs"
              disabled={locked}
              value={rows[w.id]?.cost ?? undefined}
              onChange={(v) => update(w.id, "cost", v as number | null)}
              className="!w-full"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
