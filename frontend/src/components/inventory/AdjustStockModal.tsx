"use client";

import { useEffect } from "react";
import { DatePicker, InputNumber, Radio, Select } from "antd";
import dayjs, { type Dayjs } from "dayjs";

import { App, Form, Modal, TextArea } from "@/components/ui";
import { useAccounts } from "@/hooks/useAccounting";
import { useBins } from "@/hooks/useBins";
import { useAdjustStock, useOnHand } from "@/hooks/useInventory";
import { useReasons } from "@/hooks/useReasons";
import { useLots, useSerialUnits } from "@/hooks/useTracking";
import { apiErrorMessage } from "@/lib/api";
import type { InventoryItem, Warehouse } from "@/types";

interface FormValues {
  mode: "quantity" | "value";
  location_id: number;
  bin_id?: number | null;
  date: Dayjs;
  account_id?: number;
  qty_delta?: number;
  lot_id?: number | null;
  serial_numbers?: string[];
  serial_text?: string;
  unit_cost?: number;
  value_delta?: number;
  reason?: string;
  note?: string;
}

const num = (v: string | number | null | undefined) => {
  const n = Number(v);
  return Number.isNaN(n) ? 0 : n;
};

export function AdjustStockModal({
  item,
  warehouses,
  onClose,
}: {
  item: InventoryItem | null;
  warehouses: Warehouse[];
  onClose: () => void;
}) {
  const { message } = App.useApp();
  const [form] = Form.useForm<FormValues>();
  const adjust = useAdjustStock();
  const reasons = useReasons();
  const accounts = useAccounts();
  const open = !!item;

  const mode = Form.useWatch("mode", form) ?? "quantity";
  const locationId = Form.useWatch("location_id", form);
  const binId = Form.useWatch("bin_id", form);
  const qtyDelta = Form.useWatch("qty_delta", form);
  const bins = useBins(locationId, true);
  const lots = useLots(item?.tracking_mode === "lot" ? item.id : null, locationId, binId, true);
  const serials = useSerialUnits(
    item?.tracking_mode === "serial" && num(qtyDelta) < 0 ? item.id : null,
    locationId,
    binId,
    true,
    true,
  );
  const { data: available } = useOnHand(
    open ? item?.id ?? null : null,
    locationId,
    binId,
    true,
  );
  const availableQty = num(available);
  const newOnHand = availableQty + num(qtyDelta);
  const uom = item?.uom_symbol ?? "";

  const postable = (accounts.data ?? []).filter((a) => a.is_postable);

  useEffect(() => {
    if (!open) return;
    form.resetFields();
    form.setFieldsValue({
      mode: "quantity",
      location_id: warehouses.find((w) => w.is_default)?.id ?? warehouses[0]?.id,
      date: dayjs(),
    });
  }, [open, form, warehouses]);

  useEffect(() => {
    if (open && !form.getFieldValue("account_id")) {
      const adj = postable.find((a) => a.code === "5300");
      if (adj) form.setFieldValue("account_id", adj.id);
    }
  }, [open, postable, form]);

  const submit = async (values: FormValues) => {
    if (!item) return;
    const serialNumbers =
      num(values.qty_delta) < 0
        ? values.serial_numbers ?? []
        : (values.serial_text ?? "")
            .split(/[\n,]+/)
            .map((value) => value.trim().toUpperCase())
            .filter(Boolean);
    try {
      await adjust.mutateAsync({
        product_id: item.id,
        location_id: values.location_id,
        bin_id: values.bin_id ?? null,
        lot_id: values.lot_id ?? null,
        serial_numbers: item.tracking_mode === "serial" ? serialNumbers : [],
        mode: values.mode,
        qty_delta: values.mode === "quantity" ? values.qty_delta : 0,
        value_delta: values.mode === "value" ? values.value_delta : null,
        unit_cost: values.mode === "quantity" ? values.unit_cost ?? null : null,
        date: values.date.format("YYYY-MM-DD"),
        account_id: values.account_id ?? null,
        reason: values.reason || null,
        note: values.note || null,
      });
      message.success("Stock adjusted");
      onClose();
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  return (
    <Modal
      title={`Adjust stock — ${item?.name ?? ""}`}
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      okText="Adjust"
      confirmLoading={adjust.isPending}
      destroyOnHidden
      width={600}
    >
      <Form<FormValues>
        form={form}
        layout="vertical"
        onFinish={submit}
        onValuesChange={(changed) => {
          if ("location_id" in changed) {
            form.setFieldValue("bin_id", undefined);
            form.setFieldValue("lot_id", undefined);
            form.setFieldValue("serial_numbers", []);
          }
          if ("bin_id" in changed) {
            form.setFieldValue("lot_id", undefined);
            form.setFieldValue("serial_numbers", []);
          }
          if ("qty_delta" in changed) {
            form.setFieldValue("serial_numbers", []);
            form.setFieldValue("serial_text", undefined);
          }
        }}
        className="pt-2"
      >
        <Form.Item name="mode">
          <Radio.Group optionType="button" buttonStyle="solid">
            <Radio value="quantity">Quantity adjustment</Radio>
            <Radio value="value">Value adjustment</Radio>
          </Radio.Group>
        </Form.Item>

        <div className={`grid grid-cols-1 gap-4 ${bins.data?.length ? "md:grid-cols-3" : "md:grid-cols-2"}`}>
          <Form.Item name="date" label="Date" rules={[{ required: true }]}>
            <DatePicker className="!w-full" format="DD MMM YYYY" allowClear={false} />
          </Form.Item>
          <Form.Item name="location_id" label="Warehouse" rules={[{ required: true }]}>
            <Select options={warehouses.map((w) => ({ value: w.id, label: w.name }))} />
          </Form.Item>
          {!!bins.data?.length && (
            <Form.Item name="bin_id" label="Bin">
              <Select
                allowClear
                placeholder="Unassigned"
                loading={bins.isLoading}
                options={bins.data.map((bin) => ({
                  value: bin.id,
                  label: `${bin.code} — ${bin.name}`,
                }))}
              />
            </Form.Item>
          )}
        </div>

        {mode === "quantity" && item?.tracking_mode === "lot" && (
          <Form.Item
            name="lot_id"
            label="Batch / lot"
            rules={[{ required: true, message: "Select the lot being adjusted" }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              loading={lots.isLoading}
              placeholder="Select lot"
              options={(lots.data ?? []).map((lot) => ({
                value: lot.id,
                label: `${lot.lot_number} · ${Number(lot.quantity)} available${
                  lot.expiry_date ? ` · expires ${dayjs(lot.expiry_date).format("DD MMM YYYY")}` : ""
                }`,
              }))}
            />
          </Form.Item>
        )}

        {mode === "quantity" && item?.tracking_mode === "serial" && num(qtyDelta) < 0 && (
          <Form.Item
            name="serial_numbers"
            label="Serial numbers removed"
            rules={[{ required: true, message: "Select serial numbers" }]}
          >
            <Select
              mode="multiple"
              showSearch
              optionFilterProp="label"
              loading={serials.isLoading}
              placeholder="Select serial numbers"
              options={(serials.data ?? []).map((serial) => ({
                value: serial.serial_number,
                label: serial.serial_number,
              }))}
            />
          </Form.Item>
        )}

        {mode === "quantity" && item?.tracking_mode === "serial" && num(qtyDelta) > 0 && (
          <Form.Item
            name="serial_text"
            label="Serial numbers added"
            rules={[{ required: true, message: "Enter serial numbers" }]}
            extra="Enter one serial number per line. The count must match the adjusted quantity."
          >
            <TextArea rows={5} placeholder={"SN-0001\nSN-0002"} />
          </Form.Item>
        )}

        <Form.Item
          name="account_id"
          label="Adjustment account"
          extra="Where the inventory gain or loss is booked."
        >
          <Select
            showSearch
            optionFilterProp="label"
            loading={accounts.isLoading}
            options={postable.map((a) => ({ value: a.id, label: `${a.code} — ${a.name}` }))}
          />
        </Form.Item>

        {mode === "quantity" ? (
          <>
            <div className="mb-4 grid grid-cols-1 gap-3 rounded-lg bg-slate-50 p-3 sm:grid-cols-2 sm:gap-4">
              <div>
                <div className="text-xs text-gray-400">Quantity available</div>
                <div className="text-lg font-semibold tabular-nums">
                  {availableQty} {uom}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-400">New quantity on hand</div>
                <div className="text-lg font-semibold tabular-nums">
                  {newOnHand} {uom}
                </div>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
              <Form.Item
                name="qty_delta"
                label="Quantity adjusted"
                rules={[{ required: true, message: "Enter a quantity" }]}
                extra="Negative removes stock (e.g. +10 or -5)."
              >
                <InputNumber className="!w-full" placeholder="e.g. +10 or -5" />
              </Form.Item>
              <Form.Item name="unit_cost" label="Cost price">
                <InputNumber className="!w-full" min={0} placeholder="Item's cost" />
              </Form.Item>
            </div>
          </>
        ) : (
          <Form.Item
            name="value_delta"
            label="Adjusted value"
            rules={[{ required: true, message: "Enter a value" }]}
            extra="Revalues stock without changing quantity. Negative writes the value down."
          >
            <InputNumber className="!w-full" placeholder="e.g. +500 or -250" />
          </Form.Item>
        )}

        <Form.Item name="reason" label="Reason">
          <Select
            allowClear
            placeholder="Select a reason"
            loading={reasons.isLoading}
            options={(reasons.data ?? []).map((r) => ({ value: r.name, label: r.name }))}
          />
        </Form.Item>

        <Form.Item name="note" label="Description">
          <TextArea rows={3} maxLength={500} placeholder="Notes (optional)" />
        </Form.Item>
      </Form>
    </Modal>
  );
}
