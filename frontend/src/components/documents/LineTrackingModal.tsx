"use client";

import { useEffect, useMemo, useState } from "react";
import { DatePicker, InputNumber } from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { Plus, Trash2 } from "lucide-react";

import { App, Button, Form, Input, Modal, Select, TextArea } from "@/components/ui";
import { useLots, useSerialUnits } from "@/hooks/useTracking";
import type { LotAllocation, TrackingMode } from "@/types";

interface LotRow {
  lot_id?: number | null;
  lot_number?: string | null;
  manufactured_date?: Dayjs | null;
  expiry_date?: Dayjs | null;
  quantity?: number | null;
}

interface LotForm {
  allocations: LotRow[];
}

export function LineTrackingModal({
  open,
  productId,
  productName,
  trackingMode,
  inbound,
  warehouseId,
  binId,
  quantity,
  allocations,
  serialNumbers,
  onSave,
  onClose,
}: {
  open: boolean;
  productId: number | null;
  productName: string;
  trackingMode: TrackingMode;
  inbound: boolean;
  warehouseId?: number | null;
  binId?: number | null;
  quantity: number;
  allocations: LotAllocation[];
  serialNumbers: string[];
  onSave: (allocations: LotAllocation[], serialNumbers: string[]) => void;
  onClose: () => void;
}) {
  const { message } = App.useApp();
  const [form] = Form.useForm<LotForm>();
  const [serialText, setSerialText] = useState(() => serialNumbers.join("\n"));
  const [selectedSerials, setSelectedSerials] = useState<string[]>(() => serialNumbers);
  const lots = useLots(
    productId,
    inbound ? undefined : warehouseId,
    inbound ? undefined : binId,
    !inbound,
  );
  const serials = useSerialUnits(
    inbound ? null : productId,
    warehouseId,
    binId,
    true,
    !inbound,
  );

  useEffect(() => {
    if (!open) return;
    form.setFieldsValue({
      allocations: allocations.length
        ? allocations.map((allocation) => ({
            lot_id: allocation.lot_id ?? allocation.lot?.id ?? null,
            lot_number: allocation.lot_number ?? null,
            manufactured_date: allocation.manufactured_date
              ? dayjs(allocation.manufactured_date)
              : null,
            expiry_date: allocation.expiry_date ? dayjs(allocation.expiry_date) : null,
            quantity: Number(allocation.quantity),
          }))
        : [{ quantity }],
    });
  }, [allocations, form, open, quantity]);

  const availableSerialOptions = useMemo(
    () =>
      (serials.data ?? []).map((serial) => ({
        value: serial.serial_number,
        label: serial.serial_number,
      })),
    [serials.data],
  );

  const save = async () => {
    if (trackingMode === "lot") {
      try {
        const values = await form.validateFields();
        const normalized: LotAllocation[] = values.allocations.map((allocation) => ({
          lot_id: allocation.lot_id ?? null,
          lot_number: allocation.lot_id ? null : allocation.lot_number?.trim() || null,
          manufactured_date: allocation.manufactured_date?.format("YYYY-MM-DD") ?? null,
          expiry_date: allocation.expiry_date?.format("YYYY-MM-DD") ?? null,
          quantity: Number(allocation.quantity),
        }));
        const identities = normalized.map((allocation) =>
          allocation.lot_id != null
            ? `id:${allocation.lot_id}`
            : `number:${allocation.lot_number?.toUpperCase()}`,
        );
        if (new Set(identities).size !== identities.length) {
          message.error("Each lot can only be allocated once");
          return;
        }
        const allocated = normalized.reduce((sum, allocation) => sum + Number(allocation.quantity), 0);
        if (Math.abs(allocated - quantity) > 0.0001) {
          message.error(`Allocate exactly ${quantity} units`);
          return;
        }
        onSave(normalized, []);
      } catch {
        return;
      }
      return;
    }

    const normalized = inbound
      ? serialText
          .split(/[\n,]+/)
          .map((value) => value.trim().toUpperCase())
          .filter(Boolean)
      : selectedSerials;
    if (new Set(normalized).size !== normalized.length) {
      message.error("Serial numbers must be unique");
      return;
    }
    if (!Number.isInteger(quantity) || normalized.length !== quantity) {
      message.error(`Enter exactly ${quantity} serial numbers`);
      return;
    }
    onSave([], normalized);
  };

  return (
    <Modal
      title={`${trackingMode === "lot" ? "Lot allocation" : "Serial numbers"} — ${productName}`}
      open={open}
      onCancel={onClose}
      onOk={save}
      okText="Apply"
      width={trackingMode === "lot" ? 820 : 620}
      destroyOnHidden
    >
      {trackingMode === "lot" ? (
        <Form<LotForm> form={form} layout="vertical" className="pt-2">
          <p className="mb-4 text-sm text-gray-500">
            {inbound
              ? "Select an existing lot or leave it blank to register a new batch."
              : "Lots are ordered by earliest expiry first (FEFO)."}
          </p>
          <Form.List name="allocations">
            {(fields, { add, remove }) => (
              <div className="space-y-3">
                {fields.map((field) => (
                  <div
                    key={field.key}
                    className="grid grid-cols-1 gap-3 rounded-lg border border-gray-200 p-3 md:grid-cols-[1.3fr_1fr_1fr_1fr_110px_36px]"
                  >
                    <Form.Item name={[field.name, "lot_id"]} label="Existing lot" className="!mb-0">
                      <Select
                        allowClear={inbound}
                        showSearch
                        optionFilterProp="label"
                        placeholder={inbound ? "New lot" : "Select lot"}
                        loading={lots.isLoading}
                        options={(lots.data ?? []).map((lot) => ({
                          value: lot.id,
                          label: `${lot.lot_number} · ${Number(lot.quantity)} available${
                            lot.expiry_date ? ` · exp ${dayjs(lot.expiry_date).format("DD MMM YYYY")}` : ""
                          }`,
                          disabled: !inbound && Number(lot.quantity) <= 0,
                        }))}
                      />
                    </Form.Item>
                    {inbound ? (
                      <Form.Item
                        noStyle
                        shouldUpdate={(previous, current) =>
                          previous.allocations?.[field.name]?.lot_id !==
                          current.allocations?.[field.name]?.lot_id
                        }
                      >
                        {({ getFieldValue }) =>
                          getFieldValue(["allocations", field.name, "lot_id"]) ? (
                            <div />
                          ) : (
                            <Form.Item
                              name={[field.name, "lot_number"]}
                              label="New lot number"
                              rules={[{ required: true, message: "Enter lot number" }]}
                              className="!mb-0"
                            >
                              <Input placeholder="BATCH-001" />
                            </Form.Item>
                          )
                        }
                      </Form.Item>
                    ) : (
                      <div />
                    )}
                    <Form.Item
                      name={[field.name, "manufactured_date"]}
                      label="Manufactured"
                      className="!mb-0"
                    >
                      <DatePicker className="!w-full" disabled={!inbound} format="DD MMM YYYY" />
                    </Form.Item>
                    <Form.Item name={[field.name, "expiry_date"]} label="Expiry" className="!mb-0">
                      <DatePicker className="!w-full" disabled={!inbound} format="DD MMM YYYY" />
                    </Form.Item>
                    <Form.Item
                      name={[field.name, "quantity"]}
                      label="Quantity"
                      rules={[{ required: true, message: "Required" }]}
                      className="!mb-0"
                    >
                      <InputNumber className="!w-full" min={0.001} precision={3} />
                    </Form.Item>
                    <Button
                      type="text"
                      danger
                      className="!mt-7"
                      icon={<Trash2 size={14} />}
                      disabled={fields.length === 1}
                      onClick={() => remove(field.name)}
                    />
                  </div>
                ))}
                <Button icon={<Plus size={14} />} onClick={() => add({ quantity: 0 })}>
                  Add lot
                </Button>
              </div>
            )}
          </Form.List>
        </Form>
      ) : inbound ? (
        <div className="pt-2">
          <p className="mb-3 text-sm text-gray-500">
            Enter one serial number per line. Commas are also accepted.
          </p>
          <TextArea
            rows={10}
            value={serialText}
            onChange={(event) => setSerialText(event.target.value)}
            placeholder={"SN-0001\nSN-0002"}
          />
        </div>
      ) : (
        <div className="pt-2">
          <p className="mb-3 text-sm text-gray-500">
            Select the exact serial numbers being dispatched from this warehouse and bin.
          </p>
          <Select
            mode="multiple"
            value={selectedSerials}
            onChange={setSelectedSerials}
            options={availableSerialOptions}
            loading={serials.isLoading}
            placeholder="Select serial numbers"
            className="w-full"
            showSearch
            optionFilterProp="label"
          />
        </div>
      )}
    </Modal>
  );
}
