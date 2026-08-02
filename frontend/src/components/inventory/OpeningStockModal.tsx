"use client";

import { useEffect, useMemo } from "react";
import { DatePicker, InputNumber, Spin } from "antd";
import dayjs, { type Dayjs } from "dayjs";

import { App, Form, Modal } from "@/components/ui";
import { useBins } from "@/hooks/useBins";
import { useCurrency } from "@/hooks/useCurrency";
import { useOpeningStock, useSetOpeningStock } from "@/hooks/useInventory";
import { apiErrorMessage } from "@/lib/api";
import type { Bin, Warehouse } from "@/types";

interface RowValue {
  quantity?: number | null;
  unit_cost?: number | null;
}

interface FormValues {
  date: Dayjs;
  entries: Record<string, RowValue | undefined>;
}

const entryKey = (locationId: number, binId: number | null) =>
  `${locationId}:${binId ?? "unassigned"}`;

export function OpeningStockModal({
  item,
  warehouses,
  onClose,
}: {
  item: { id: number; name: string; uom: string } | null;
  warehouses: Warehouse[];
  onClose: () => void;
}) {
  const { message } = App.useApp();
  const { currency, money } = useCurrency();
  const opening = useOpeningStock(item?.id ?? null);
  const bins = useBins();
  const saveOpening = useSetOpeningStock();
  const [form] = Form.useForm<FormValues>();
  const open = item != null;
  const editable = opening.data?.editable === true;

  useEffect(() => {
    if (!open) return;
    form.resetFields();
    form.setFieldsValue({
      date: dayjs(),
      entries: Object.fromEntries(
        (opening.data?.entries ?? []).map((entry) => [
          entryKey(entry.location_id, entry.bin_id),
          {
            quantity: Number(entry.quantity),
            unit_cost: entry.unit_cost == null ? null : Number(entry.unit_cost),
          },
        ]),
      ),
    });
  }, [form, open, opening.data]);

  const openingKeys = useMemo(
    () =>
      new Set(
        (opening.data?.entries ?? []).map((entry) =>
          entryKey(entry.location_id, entry.bin_id),
        ),
      ),
    [opening.data],
  );
  const visibleRows = useMemo(() => {
    const result: { key: string; warehouse: Warehouse; bin: Bin | null }[] = [];
    for (const warehouse of warehouses) {
      const unassignedKey = entryKey(warehouse.id, null);
      if (warehouse.is_active || openingKeys.has(unassignedKey)) {
        result.push({ key: unassignedKey, warehouse, bin: null });
      }
      for (const bin of (bins.data ?? []).filter((row) => row.location_id === warehouse.id)) {
        const key = entryKey(warehouse.id, bin.id);
        if ((warehouse.is_active && bin.is_active) || openingKeys.has(key)) {
          result.push({ key, warehouse, bin });
        }
      }
    }
    return result;
  }, [bins.data, openingKeys, warehouses]);

  const rows = Form.useWatch("entries", form) ?? {};

  const submit = async (values: FormValues) => {
    if (!item || !editable) return;
    try {
      await saveOpening.mutateAsync({
        product_id: item.id,
        date: values.date.format("YYYY-MM-DD"),
        entries: visibleRows
          .filter(({ warehouse, bin }) => warehouse.is_active && (bin == null || bin.is_active))
          .map(({ key, warehouse, bin }) => ({
            location_id: warehouse.id,
            bin_id: bin?.id ?? null,
            quantity: Number(values.entries?.[key]?.quantity || 0),
            unit_cost: values.entries?.[key]?.unit_cost ?? null,
          })),
      });
      message.success("Opening stock saved");
      onClose();
    } catch (error) {
      message.error(apiErrorMessage(error));
    }
  };

  return (
    <Modal
      title={`Opening stock — ${item?.name ?? ""}`}
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      okText={editable ? "Save opening stock" : "Opening stock locked"}
      okButtonProps={{ disabled: !editable }}
      confirmLoading={saveOpening.isPending}
      destroyOnHidden
      width={760}
    >
      {opening.isLoading || bins.isLoading ? (
        <div className="flex min-h-48 items-center justify-center">
          <Spin />
        </div>
      ) : (
        <Form<FormValues>
          form={form}
          onFinish={submit}
          initialValues={{ date: dayjs(), entries: {} }}
          className="space-y-4 pt-2"
        >
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
            <p className="max-w-xl text-sm text-gray-500">
              Enter stock already owned when this item was added to VinesFlow. It records inventory
              value but does not create a purchase order or supplier payable.
            </p>
            <Form.Item name="date" noStyle rules={[{ required: true }]}>
              <DatePicker format="DD MMM YYYY" allowClear={false} disabled={!editable} />
            </Form.Item>
          </div>

          {!editable && (
            <div className="rounded-lg border border-gray-200 bg-slate-50 px-4 py-3 text-sm text-gray-600">
              Opening stock is locked because inventory transactions already exist. Use Adjust
              Stock to correct the quantity or value.
            </div>
          )}

          <div className="overflow-hidden rounded-lg border border-gray-200">
            <div className="hidden grid-cols-[minmax(0,1fr)_150px_180px_120px] gap-4 bg-slate-50 px-4 py-2 text-xs font-medium uppercase tracking-wide text-gray-500 sm:grid">
              <span>Warehouse / bin</span>
              <span>Quantity</span>
              <span>Rate per unit</span>
              <span className="text-right">Value</span>
            </div>
            {visibleRows.map(({ key, warehouse, bin }) => {
              const row = rows[key] ?? {};
              const value = Number(row.quantity || 0) * Number(row.unit_cost || 0);
              const disabled = !editable || !warehouse.is_active || bin?.is_active === false;
              return (
                <div
                  key={key}
                  className="grid grid-cols-1 items-center gap-3 border-t border-gray-100 px-4 py-3 first:border-t-0 sm:grid-cols-[minmax(0,1fr)_150px_180px_120px] sm:gap-4"
                >
                  <div>
                    <div className="text-sm font-medium text-slate-800">
                      {warehouse.name}
                    </div>
                    <div className="text-xs text-gray-400">
                      {bin ? `${bin.code} — ${bin.name}` : "Unassigned to a bin"}
                      {disabled && editable ? " · Inactive" : ""}
                    </div>
                  </div>
                  <label>
                    <span className="mb-1 block text-xs text-gray-500 sm:hidden">Quantity</span>
                    <Form.Item name={["entries", key, "quantity"]} noStyle>
                      <InputNumber
                        className="!w-full"
                        min={0}
                        precision={3}
                        controls={false}
                        placeholder="0"
                        disabled={disabled}
                        addonAfter={item?.uom || undefined}
                      />
                    </Form.Item>
                  </label>
                  <label>
                    <span className="mb-1 block text-xs text-gray-500 sm:hidden">
                      Rate per unit
                    </span>
                    <Form.Item name={["entries", key, "unit_cost"]} noStyle>
                      <InputNumber
                        className="!w-full"
                        min={0}
                        precision={4}
                        controls={false}
                        prefix={currency}
                        placeholder="Optional"
                        disabled={disabled}
                      />
                    </Form.Item>
                  </label>
                  <div className="text-right text-sm font-medium tabular-nums text-slate-700">
                    <span className="mr-2 text-xs font-normal text-gray-500 sm:hidden">Value</span>
                    {money(value)}
                  </div>
                </div>
              );
            })}
            {!visibleRows.length && (
              <div className="px-4 py-8 text-center text-sm text-gray-500">
                Create an active warehouse before setting opening stock.
              </div>
            )}
          </div>

          {Object.values(rows).some(
            (row) => Number(row?.quantity || 0) > 0 && row?.unit_cost == null,
          ) && (
            <p className="text-xs text-gray-500">
              Quantity without a rate updates stock but does not add inventory value to accounting.
            </p>
          )}
        </Form>
      )}
    </Modal>
  );
}
