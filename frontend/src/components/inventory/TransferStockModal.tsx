"use client";

import { useEffect } from "react";
import { InputNumber, Select } from "antd";

import { App, Form, Input, Modal } from "@/components/ui";
import { useBins } from "@/hooks/useBins";
import { useTransferStock } from "@/hooks/useInventory";
import { useLots, useSerialUnits } from "@/hooks/useTracking";
import { apiErrorMessage } from "@/lib/api";
import type { InventoryItem, Warehouse } from "@/types";

interface FormValues {
  from_location_id: number;
  to_location_id: number;
  from_bin_id?: number | null;
  to_bin_id?: number | null;
  lot_id?: number | null;
  serial_numbers?: string[];
  quantity: number;
  note?: string;
}

export function TransferStockModal({
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
  const transfer = useTransferStock();
  const bins = useBins(undefined, true);
  const open = !!item;
  const fromLocationId = Form.useWatch("from_location_id", form);
  const toLocationId = Form.useWatch("to_location_id", form);
  const fromBinId = Form.useWatch("from_bin_id", form);
  const lots = useLots(
    item?.tracking_mode === "lot" ? item.id : null,
    fromLocationId,
    fromBinId,
    true,
  );
  const serials = useSerialUnits(
    item?.tracking_mode === "serial" ? item.id : null,
    fromLocationId,
    fromBinId,
    true,
    true,
  );

  useEffect(() => {
    if (open) form.resetFields();
  }, [open, form]);

  const submit = async (values: FormValues) => {
    if (!item) return;
    if (
      values.from_location_id === values.to_location_id &&
      (values.from_bin_id ?? null) === (values.to_bin_id ?? null)
    ) {
      message.error("Source and destination must differ");
      return;
    }
    try {
      await transfer.mutateAsync({
        product_id: item.id,
        from_location_id: values.from_location_id,
        to_location_id: values.to_location_id,
        from_bin_id: values.from_bin_id ?? null,
        to_bin_id: values.to_bin_id ?? null,
        lot_id: values.lot_id ?? null,
        serial_numbers: values.serial_numbers ?? [],
        quantity: values.quantity,
        note: values.note || null,
      });
      message.success("Stock transferred");
      onClose();
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const options = warehouses.map((w) => ({ value: w.id, label: w.name }));
  const binOptions = (locationId?: number) =>
    (bins.data ?? [])
      .filter((bin) => bin.location_id === locationId)
      .map((bin) => ({ value: bin.id, label: `${bin.code} — ${bin.name}` }));
  const fromBins = binOptions(fromLocationId);
  const toBins = binOptions(toLocationId);

  return (
    <Modal
      title={`Transfer stock — ${item?.name ?? ""}`}
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      okText="Transfer"
      confirmLoading={transfer.isPending}
      destroyOnHidden
    >
      <Form<FormValues>
        form={form}
        layout="vertical"
        onFinish={submit}
        onValuesChange={(changed) => {
          if ("from_location_id" in changed) {
            form.setFieldValue("from_bin_id", undefined);
            form.setFieldValue("lot_id", undefined);
            form.setFieldValue("serial_numbers", []);
          }
          if ("to_location_id" in changed) form.setFieldValue("to_bin_id", undefined);
          if ("from_bin_id" in changed) {
            form.setFieldValue("lot_id", undefined);
            form.setFieldValue("serial_numbers", []);
          }
        }}
        className="pt-2"
      >
        <div className="grid grid-cols-1 gap-x-4 md:grid-cols-2">
          <Form.Item name="from_location_id" label="From" rules={[{ required: true, message: "Select source" }]}>
            <Select options={options} placeholder="Source warehouse" />
          </Form.Item>
          <Form.Item name="to_location_id" label="To" rules={[{ required: true, message: "Select destination" }]}>
            <Select options={options} placeholder="Destination warehouse" />
          </Form.Item>
        </div>
        {(fromBins.length > 0 || toBins.length > 0) && (
          <div className="grid grid-cols-1 gap-x-4 md:grid-cols-2">
            <Form.Item name="from_bin_id" label="From bin">
              <Select
                options={fromBins}
                placeholder="Unassigned"
                allowClear
                disabled={!fromLocationId || fromBins.length === 0}
              />
            </Form.Item>
            <Form.Item name="to_bin_id" label="To bin">
              <Select
                options={toBins}
                placeholder="Unassigned"
                allowClear
                disabled={!toLocationId || toBins.length === 0}
              />
            </Form.Item>
          </div>
        )}
        {item?.tracking_mode === "lot" && (
          <Form.Item
            name="lot_id"
            label="Batch / lot"
            rules={[{ required: true, message: "Select the lot to transfer" }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              loading={lots.isLoading}
              placeholder="Select lot"
              options={(lots.data ?? []).map((lot) => ({
                value: lot.id,
                label: `${lot.lot_number} · ${Number(lot.quantity)} available`,
                disabled: Number(lot.quantity) <= 0,
              }))}
            />
          </Form.Item>
        )}
        {item?.tracking_mode === "serial" && (
          <Form.Item
            name="serial_numbers"
            label="Serial numbers"
            rules={[{ required: true, message: "Select serial numbers to transfer" }]}
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
              onChange={(values) => form.setFieldValue("quantity", values.length)}
            />
          </Form.Item>
        )}
        <Form.Item name="quantity" label="Quantity" rules={[{ required: true, message: "Enter a quantity" }]}> 
          <InputNumber
            className="!w-full"
            min={0.001}
            placeholder="e.g. 5"
            disabled={item?.tracking_mode === "serial"}
          />
        </Form.Item>
        <Form.Item name="note" label="Note">
          <Input placeholder="Reason (optional)" />
        </Form.Item>
      </Form>
    </Modal>
  );
}
