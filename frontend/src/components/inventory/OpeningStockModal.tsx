"use client";

import { useEffect, useMemo } from "react";
import { DatePicker, InputNumber, Select, Spin } from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { Plus, Trash2 } from "lucide-react";

import { App, Button, Form, Input, Modal, TextArea } from "@/components/ui";
import { useBins } from "@/hooks/useBins";
import { useCurrency } from "@/hooks/useCurrency";
import { useOpeningStock, useSetOpeningStock } from "@/hooks/useInventory";
import { useLots } from "@/hooks/useTracking";
import { apiErrorMessage } from "@/lib/api";
import type { Bin, Warehouse } from "@/types";

interface RowValue {
  quantity?: number | null;
  unit_cost?: number | null;
}

interface FormValues {
  date: Dayjs;
  entries: Record<string, RowValue | undefined>;
  tracked_entries: TrackedRowValue[];
}

interface TrackedRowValue {
  location_id?: number | null;
  bin_id?: number | null;
  lot_id?: number | null;
  lot_number?: string | null;
  manufactured_date?: Dayjs | null;
  expiry_date?: Dayjs | null;
  serial_text?: string;
  quantity?: number | null;
  unit_cost?: number | null;
}

const entryKey = (locationId: number, binId: number | null) =>
  `${locationId}:${binId ?? "unassigned"}`;

export function OpeningStockModal({
  item,
  warehouses,
  onClose,
}: {
  item: {
    id: number;
    name: string;
    uom: string;
    tracking_mode: "none" | "lot" | "serial";
  } | null;
  warehouses: Warehouse[];
  onClose: () => void;
}) {
  const { message } = App.useApp();
  const { currency, money } = useCurrency();
  const opening = useOpeningStock(item?.id ?? null);
  const bins = useBins();
  const lots = useLots(item?.tracking_mode === "lot" ? item.id : null);
  const saveOpening = useSetOpeningStock();
  const [form] = Form.useForm<FormValues>();
  const open = item != null;
  const trackingMode = item?.tracking_mode ?? "none";
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
      tracked_entries:
        item?.tracking_mode === "none"
          ? []
          : (opening.data?.entries ?? []).map((entry) => {
              const lot = lots.data?.find((candidate) => candidate.id === entry.lot_id);
              return {
                location_id: entry.location_id,
                bin_id: entry.bin_id,
                lot_id: entry.lot_id,
                lot_number: lot?.lot_number ?? null,
                manufactured_date: lot?.manufactured_date
                  ? dayjs(lot.manufactured_date)
                  : null,
                expiry_date: lot?.expiry_date ? dayjs(lot.expiry_date) : null,
                serial_text: entry.serial_numbers.join("\n"),
                quantity: Number(entry.quantity),
                unit_cost: entry.unit_cost == null ? null : Number(entry.unit_cost),
              };
            }),
    });
  }, [form, item?.tracking_mode, lots.data, open, opening.data]);

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
  const trackedRows = Form.useWatch("tracked_entries", form) ?? [];

  const submit = async (values: FormValues) => {
    if (!item || !editable) return;
    try {
      const entries =
        item.tracking_mode === "none"
          ? visibleRows
              .filter(({ warehouse, bin }) => warehouse.is_active && (bin == null || bin.is_active))
              .map(({ key, warehouse, bin }) => ({
                location_id: warehouse.id,
                bin_id: bin?.id ?? null,
                quantity: Number(values.entries?.[key]?.quantity || 0),
                unit_cost: values.entries?.[key]?.unit_cost ?? null,
              }))
          : (values.tracked_entries ?? []).map((entry) => {
              const serialNumbers = (entry.serial_text ?? "")
                .split(/[\n,]+/)
                .map((value) => value.trim().toUpperCase())
                .filter(Boolean);
              return {
                location_id: Number(entry.location_id),
                bin_id: entry.bin_id ?? null,
                lot_id: entry.lot_id ?? null,
                lot_number: entry.lot_id ? null : entry.lot_number?.trim() || null,
                manufactured_date: entry.manufactured_date?.format("YYYY-MM-DD") ?? null,
                expiry_date: entry.expiry_date?.format("YYYY-MM-DD") ?? null,
                serial_numbers: item.tracking_mode === "serial" ? serialNumbers : [],
                quantity:
                  item.tracking_mode === "serial" ? serialNumbers.length : Number(entry.quantity || 0),
                unit_cost: entry.unit_cost ?? null,
              };
            });
      await saveOpening.mutateAsync({
        product_id: item.id,
        date: values.date.format("YYYY-MM-DD"),
        entries,
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
          initialValues={{ date: dayjs(), entries: {}, tracked_entries: [] }}
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

          {item?.tracking_mode === "none" ? (
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

          ) : (
            <Form.List name="tracked_entries">
              {(fields, { add, remove }) => (
                <div className="space-y-3">
                  {fields.map((field) => (
                    <div key={field.key} className="rounded-lg border border-gray-200 p-4">
                      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                        <Form.Item
                          name={[field.name, "location_id"]}
                          label="Warehouse"
                          rules={[{ required: true, message: "Select a warehouse" }]}
                        >
                          <Select
                            options={warehouses
                              .filter((warehouse) => warehouse.is_active)
                              .map((warehouse) => ({ value: warehouse.id, label: warehouse.name }))}
                          />
                        </Form.Item>
                        <Form.Item noStyle shouldUpdate>
                          {({ getFieldValue }) => {
                            const locationId = getFieldValue([
                              "tracked_entries",
                              field.name,
                              "location_id",
                            ]);
                            const options = (bins.data ?? [])
                              .filter((bin) => bin.location_id === locationId && bin.is_active)
                              .map((bin) => ({ value: bin.id, label: `${bin.code} — ${bin.name}` }));
                            return (
                              <Form.Item name={[field.name, "bin_id"]} label="Bin">
                                <Select options={options} allowClear placeholder="Unassigned" />
                              </Form.Item>
                            );
                          }}
                        </Form.Item>
                      </div>

                      {trackingMode === "lot" ? (
                        <>
                          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                            <Form.Item name={[field.name, "lot_id"]} label="Existing lot">
                              <Select
                                allowClear
                                showSearch
                                optionFilterProp="label"
                                placeholder="Create a new lot"
                                options={(lots.data ?? []).map((lot) => ({
                                  value: lot.id,
                                  label: lot.lot_number,
                                }))}
                              />
                            </Form.Item>
                            <Form.Item noStyle shouldUpdate>
                              {({ getFieldValue }) =>
                                getFieldValue(["tracked_entries", field.name, "lot_id"]) ? (
                                  <div />
                                ) : (
                                  <Form.Item
                                    name={[field.name, "lot_number"]}
                                    label="New lot number"
                                    rules={[{ required: true, message: "Enter a lot number" }]}
                                  >
                                    <Input placeholder="BATCH-001" />
                                  </Form.Item>
                                )
                              }
                            </Form.Item>
                          </div>
                          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                            <Form.Item name={[field.name, "manufactured_date"]} label="Manufactured date">
                              <DatePicker className="!w-full" format="DD MMM YYYY" />
                            </Form.Item>
                            <Form.Item name={[field.name, "expiry_date"]} label="Expiry date">
                              <DatePicker className="!w-full" format="DD MMM YYYY" />
                            </Form.Item>
                          </div>
                        </>
                      ) : (
                        <Form.Item
                          name={[field.name, "serial_text"]}
                          label="Serial numbers"
                          rules={[{ required: true, message: "Enter serial numbers" }]}
                          extra="One serial per line. Quantity is calculated from the serial count."
                        >
                          <TextArea rows={5} placeholder={"SN-0001\nSN-0002"} />
                        </Form.Item>
                      )}

                      <div className="grid grid-cols-1 items-end gap-3 md:grid-cols-[1fr_1fr_auto]">
                        {trackingMode === "lot" ? (
                          <Form.Item
                            name={[field.name, "quantity"]}
                            label="Quantity"
                            rules={[{ required: true, message: "Enter quantity" }]}
                          >
                            <InputNumber className="!w-full" min={0.001} precision={3} />
                          </Form.Item>
                        ) : (
                          <div className="mb-6 text-sm text-gray-500">
                            {((trackedRows[field.name]?.serial_text ?? "")
                              .split(/[\n,]+/)
                              .map((value) => value.trim())
                              .filter(Boolean).length)} serials
                          </div>
                        )}
                        <Form.Item name={[field.name, "unit_cost"]} label="Rate per unit">
                          <InputNumber className="!w-full" min={0} precision={4} prefix={currency} />
                        </Form.Item>
                        <Button
                          danger
                          type="text"
                          className="!mb-6"
                          icon={<Trash2 size={15} />}
                          onClick={() => remove(field.name)}
                          disabled={!editable}
                        />
                      </div>
                    </div>
                  ))}
                  {editable && (
                    <Button
                      icon={<Plus size={15} />}
                      onClick={() =>
                        add({
                          location_id: warehouses.find((warehouse) => warehouse.is_default)?.id,
                          quantity: trackingMode === "lot" ? 0 : undefined,
                        })
                      }
                    >
                      Add {trackingMode === "lot" ? "lot" : "serial stock"}
                    </Button>
                  )}
                </div>
              )}
            </Form.List>
          )}

          {item?.tracking_mode === "none" && Object.values(rows).some(
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
