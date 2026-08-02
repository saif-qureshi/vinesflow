"use client";

import { useEffect, useMemo } from "react";
import { DatePicker, InputNumber, Spin } from "antd";
import dayjs, { type Dayjs } from "dayjs";

import { App, Form, Modal } from "@/components/ui";
import { useCurrency } from "@/hooks/useCurrency";
import { useOpeningStock, useSetOpeningStock } from "@/hooks/useInventory";
import { apiErrorMessage } from "@/lib/api";
import type { Warehouse } from "@/types";

interface RowValue {
  quantity?: number | null;
  unit_cost?: number | null;
}

interface FormValues {
  date: Dayjs;
  entries: Record<number, RowValue | undefined>;
}

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
          entry.location_id,
          {
            quantity: Number(entry.quantity),
            unit_cost: entry.unit_cost == null ? null : Number(entry.unit_cost),
          },
        ]),
      ),
    });
  }, [form, open, opening.data]);

  const openingLocations = useMemo(
    () => new Set((opening.data?.entries ?? []).map((entry) => entry.location_id)),
    [opening.data],
  );
  const visibleWarehouses = warehouses.filter(
    (warehouse) => warehouse.is_active || openingLocations.has(warehouse.id),
  );

  const rows = Form.useWatch("entries", form) ?? {};

  const submit = async (values: FormValues) => {
    if (!item || !editable) return;
    try {
      await saveOpening.mutateAsync({
        product_id: item.id,
        date: values.date.format("YYYY-MM-DD"),
        entries: warehouses
          .filter((warehouse) => warehouse.is_active)
          .map((warehouse) => ({
            location_id: warehouse.id,
            quantity: Number(values.entries?.[warehouse.id]?.quantity || 0),
            unit_cost: values.entries?.[warehouse.id]?.unit_cost ?? null,
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
      {opening.isLoading ? (
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
              <span>Warehouse</span>
              <span>Quantity</span>
              <span>Rate per unit</span>
              <span className="text-right">Value</span>
            </div>
            {visibleWarehouses.map((warehouse) => {
              const row = rows[warehouse.id] ?? {};
              const value = Number(row.quantity || 0) * Number(row.unit_cost || 0);
              const disabled = !editable || !warehouse.is_active;
              return (
                <div
                  key={warehouse.id}
                  className="grid grid-cols-1 items-center gap-3 border-t border-gray-100 px-4 py-3 first:border-t-0 sm:grid-cols-[minmax(0,1fr)_150px_180px_120px] sm:gap-4"
                >
                  <div>
                    <div className="text-sm font-medium text-slate-800">{warehouse.name}</div>
                    <div className="text-xs text-gray-400">
                      {warehouse.is_default
                        ? "Default warehouse"
                        : warehouse.is_active
                          ? "Active"
                          : "Inactive"}
                    </div>
                  </div>
                  <label>
                    <span className="mb-1 block text-xs text-gray-500 sm:hidden">Quantity</span>
                    <Form.Item name={["entries", warehouse.id, "quantity"]} noStyle>
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
                    <Form.Item name={["entries", warehouse.id, "unit_cost"]} noStyle>
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
            {!visibleWarehouses.length && (
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
