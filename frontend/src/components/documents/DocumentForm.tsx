"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { DatePicker, InputNumber, Segmented, Table } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs, { type Dayjs } from "dayjs";
import { Info, Package, Plus, ScanLine, Trash2 } from "lucide-react";

import {
  App,
  Avatar,
  Button,
  Card,
  Dropdown,
  Form,
  Input,
  Select,
  TextArea,
  Tooltip,
  Typography,
} from "@/components/ui";
import { useCurrency } from "@/hooks/useCurrency";
import { useBins } from "@/hooks/useBins";
import {
  useCreateDocument,
  useFinalizeDocument,
  useNextNumber,
  useSellableItems,
  useStockOnHand,
  useTaxRates,
  useUpdateDocument,
} from "@/hooks/useDocuments";
import { useParties } from "@/hooks/useParties";
import { useSession } from "@/hooks/useSession";
import { useWarehouses } from "@/hooks/useWarehouses";
import { apiErrorMessage } from "@/lib/api";
import type { DocumentKindConfig } from "@/lib/documentKinds";
import { FBR_SCENARIOS } from "@/lib/fbrScenarios";
import { FBR_REASONS, FBR_REASON_OTHERS } from "@/lib/fbrReasons";
import { fbrFurtherTax, fbrSalesTax } from "@/lib/fbrTax";
import { PK_PROVINCES } from "@/lib/provinces";
import type { DiscountType, DocumentInput, DocumentRecord, LotAllocation, TrackingMode } from "@/types";

import { LineTrackingModal } from "./LineTrackingModal";

interface LineRow {
  key: string;
  product_id: number | null;
  bin_id: number | null;
  description: string;
  quantity: number;
  unit_price: number;
  discount_type: DiscountType;
  discount_value: number;
  tax_rate_id: number | null;
  fbr_rate: string | null;
  stock: number | null;
  track_inventory: boolean;
  tracking_mode: TrackingMode;
  lot_allocations: LotAllocation[];
  serial_numbers: string[];
  image_url: string | null;
}

interface FormValues {
  number?: string;
  party_id: number;
  issue_date: Dayjs;
  due_date?: Dayjs | null;
  expected_shipment_date?: Dayjs | null;
  reference?: string;
  warehouse_id?: number | null;
  notes?: string;
  terms?: string;
  shipping?: number;
  adjustment?: number;
  fbr_sale_origin?: string;
  fbr_sale_destination?: string;
  fbr_scenario_id?: string;
  fbr_reason?: string;
  fbr_reason_remarks?: string;
}

let counter = 0;
const newKey = () => `line-${counter++}`;

const emptyLine = (): LineRow => ({
  key: newKey(),
  product_id: null,
  bin_id: null,
  description: "",
  quantity: 1,
  unit_price: 0,
  discount_type: "amount",
  discount_value: 0,
  tax_rate_id: null,
  fbr_rate: null,
  stock: null,
  track_inventory: false,
  tracking_mode: "none",
  lot_allocations: [],
  serial_numbers: [],
  image_url: null,
});

const lineDiscount = (row: LineRow): number => {
  const base = row.quantity * row.unit_price;
  const raw = row.discount_type === "percent" ? (base * row.discount_value) / 100 : row.discount_value;
  return Math.min(raw, base);
};

export function DocumentForm({
  config,
  document,
}: {
  config: DocumentKindConfig;
  document?: DocumentRecord;
}) {
  const router = useRouter();
  const { message } = App.useApp();
  const { currency, money } = useCurrency();
  const [form] = Form.useForm<FormValues>();
  const create = useCreateDocument(config.apiPath);
  const update = useUpdateDocument(config.apiPath);
  const finalize = useFinalizeDocument(config.apiPath);
  const saveModeRef = useRef<"draft" | "finalize">("draft");
  const usesBins = config.kind !== "sales_order" && config.kind !== "purchase_order";
  const inboundStock = ["goods_receipt", "bill", "credit_note"].includes(config.kind);

  const { data: taxRates } = useTaxRates();
  const { data: warehouses } = useWarehouses();
  const warehouseId = Form.useWatch("warehouse_id", form);
  const { data: bins } = useBins(warehouseId, true, usesBins && warehouseId != null);
  const [itemSearch, setItemSearch] = useState("");
  const { data: sellable } = useSellableItems(itemSearch, warehouseId);
  const parties = useParties(config.partyRole);
  const { currentMembership } = useSession();
  const org = currentMembership?.organization;
  const showFbr = !!org?.fbr_enabled && config.kind === "invoice";
  const showFbrReason = !!org?.fbr_enabled && config.kind === "credit_note";
  const isSandbox = org?.fbr_environment === "sandbox";
  const partyList = useMemo(
    () => parties.data?.pages.flatMap((p) => p.items) ?? [],
    [parties.data],
  );
  const selectedPartyId = Form.useWatch("party_id", form);
  const buyerRegistered = !!partyList.find((p) => p.id === selectedPartyId)?.strn;

  const [lines, setLines] = useState<LineRow[]>(() =>
    document?.lines.length
      ? document.lines.map((l) => ({
          key: newKey(),
          product_id: l.product_id,
          bin_id: usesBins ? l.bin_id : null,
          description: l.description,
          quantity: Number(l.quantity),
          unit_price: Number(l.unit_price),
          discount_type: l.discount_type,
          discount_value: Number(l.discount_value),
          tax_rate_id: l.tax_rate_id,
          fbr_rate: null,
          stock: null,
          track_inventory: false,
          tracking_mode: l.tracking_mode,
          lot_allocations: l.lot_allocations.map((allocation) => ({
            ...allocation,
            lot_id: allocation.lot_id ?? allocation.lot?.id ?? null,
          })),
          serial_numbers: l.serials.map((serial) => serial.serial_number),
          image_url: null,
        }))
      : [emptyLine()],
  );
  const [shipping, setShipping] = useState(Number(document?.shipping ?? 0));
  const [adjustment, setAdjustment] = useState(Number(document?.adjustment ?? 0));
  const [selectedKeys, setSelectedKeys] = useState<React.Key[]>([]);
  const [focusKey, setFocusKey] = useState<string | null>(null);
  const [trackingLineKey, setTrackingLineKey] = useState<string | null>(null);
  const [discountMode, setDiscountMode] = useState<DiscountType>(
    () => document?.lines[0]?.discount_type ?? "amount",
  );
  const previousWarehouseId = useRef<number | null | undefined>(document?.warehouse_id);

  const lineProductIds = useMemo(
    () => lines.map((l) => l.product_id).filter((id): id is number => id != null),
    [lines],
  );
  const { data: stockMap } = useStockOnHand(lineProductIds, warehouseId);

  const isEdit = !!document;
  const saving = create.isPending || update.isPending;
  const backHref = isEdit ? `${config.basePath}/${document.id}` : config.basePath;
  const nextNumber = useNextNumber(config.apiPath, !isEdit);

  useEffect(() => {
    if (isEdit || !warehouses?.length || form.getFieldValue("warehouse_id")) return;
    const preferred = warehouses.find((w) => w.is_default) ?? warehouses[0];
    if (preferred) form.setFieldValue("warehouse_id", preferred.id);
  }, [warehouses, isEdit, form]);

  useEffect(() => {
    if (previousWarehouseId.current === warehouseId) return;
    if (previousWarehouseId.current !== undefined) {
      setLines((prev) =>
        prev.map((line) => ({
          ...line,
          bin_id: null,
          lot_allocations: [],
          serial_numbers: [],
        })),
      );
    }
    previousWarehouseId.current = warehouseId;
  }, [warehouseId]);

  useEffect(() => {
    if (isEdit || !nextNumber.data?.number || form.getFieldValue("number")) return;
    form.setFieldValue("number", nextNumber.data.number);
  }, [nextNumber.data, isEdit, form]);

  const partyOptions = partyList.map((c) => ({
    value: c.id,
    label: c.name,
  }));
  const taxOptions = (taxRates ?? []).map((t) => ({
    value: t.id,
    label: `${t.name} (${Number(t.rate)}%)`,
  }));
  const itemOptions = (sellable ?? []).map((i) => ({
    value: i.id,
    label: i.sku ? `${i.name} · ${i.sku}` : i.name,
  }));
  const lineTracksInventory = (row: LineRow) => {
    const item = (sellable ?? []).find((candidate) => candidate.id === row.product_id);
    return item?.track_inventory ?? (row.track_inventory || row.product_id != null);
  };
  const lineTrackingMode = (row: LineRow): TrackingMode => {
    const item = (sellable ?? []).find((candidate) => candidate.id === row.product_id);
    return item?.tracking_mode ?? row.tracking_mode;
  };

  const rateOf = (id: number | null) =>
    id == null ? 0 : Number((taxRates ?? []).find((t) => t.id === id)?.rate ?? 0);

  const totals = useMemo(() => {
    let subtotal = 0;
    let discountTotal = 0;
    let taxTotal = 0;
    let furtherTotal = 0;
    for (const line of lines) {
      const base = line.quantity * line.unit_price;
      const discount = lineDiscount(line);
      const taxable = base - discount;
      subtotal += base;
      discountTotal += discount;
      if (showFbr) {
        taxTotal += fbrSalesTax(line.fbr_rate, taxable, line.quantity);
        furtherTotal += fbrFurtherTax(buyerRegistered, taxable);
      } else {
        taxTotal += (taxable * rateOf(line.tax_rate_id)) / 100;
      }
    }
    return {
      subtotal,
      discountTotal,
      taxTotal,
      furtherTotal,
      total: subtotal - discountTotal + taxTotal + furtherTotal + shipping + adjustment,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lines, shipping, adjustment, taxRates, showFbr, buyerRegistered]);

  const patchLine = (key: string, patch: Partial<LineRow>) =>
    setLines((prev) => prev.map((l) => (l.key === key ? { ...l, ...patch } : l)));

  const addLine = (focus = false) => {
    const line = { ...emptyLine(), discount_type: discountMode };
    setLines((prev) => [...prev, line]);
    if (focus) setFocusKey(line.key);
  };

  const changeDiscountMode = (mode: DiscountType) => {
    setDiscountMode(mode);
    setLines((prev) => prev.map((l) => ({ ...l, discount_type: mode })));
  };

  const removeLines = (keys: React.Key[]) => {
    setLines((prev) => {
      const next = prev.filter((l) => !keys.includes(l.key));
      return next.length ? next : [emptyLine()];
    });
    setSelectedKeys((prev) => prev.filter((k) => !keys.includes(k)));
  };

  const tabToNewRow = (row: LineRow) => (e: React.KeyboardEvent) => {
    if (e.key !== "Tab" || e.shiftKey) return;
    if (lines[lines.length - 1]?.key !== row.key) return;
    e.preventDefault();
    addLine(true);
  };

  const pickItem = (key: string, productId: number) => {
    const item = (sellable ?? []).find((i) => i.id === productId);
    const price = item ? item[config.priceField] : null;
    patchLine(key, {
      product_id: productId,
      description: item?.name ?? "",
      unit_price: price != null ? Number(price) : 0,
      fbr_rate: item?.fbr_rate ?? null,
      stock: item?.stock != null ? Number(item.stock) : null,
      track_inventory: item?.track_inventory ?? false,
      tracking_mode: item?.tracking_mode ?? "none",
      lot_allocations: [],
      serial_numbers: [],
      bin_id: null,
      image_url: item?.image_url ?? null,
    });
    setItemSearch("");
  };

  const columns: ColumnsType<LineRow> = [
    {
      title: "Item",
      key: "item",
      width: 340,
      render: (_, row) => (
        <Select
          value={row.product_id ?? undefined}
          onChange={(v) =>
            v == null
              ? patchLine(row.key, {
                  product_id: null,
                  bin_id: null,
                  stock: null,
                  track_inventory: false,
                  tracking_mode: "none",
                  lot_allocations: [],
                  serial_numbers: [],
                  image_url: null,
                })
              : pickItem(row.key, v)
          }
          onSearch={setItemSearch}
          onOpenChange={(open) => open && setItemSearch("")}
          options={itemOptions}
          placeholder="Select an item"
          showSearch
          filterOption={false}
          allowClear
          labelRender={() => {
            const live = row.product_id != null ? stockMap?.[row.product_id] : undefined;
            const stock = live != null ? Number(live) : row.stock;
            return (
              <span className="flex items-center gap-2">
                <Avatar
                  shape="square"
                  size={20}
                  src={row.image_url ?? undefined}
                  icon={<Package size={11} />}
                />
                <span className="min-w-0 flex-1 truncate">{row.description}</span>
                {row.track_inventory && stock != null && (
                  <span className={`shrink-0 text-xs ${stock < 0 ? "text-rose-500" : "text-gray-400"}`}>
                    Stock In Hand: {stock}
                  </span>
                )}
              </span>
            );
          }}
          autoFocus={row.key === focusKey}
          popupMatchSelectWidth={420}
          optionRender={(option) => {
            const item = (sellable ?? []).find((i) => i.id === option.value);
            if (!item) return option.label;
            return (
              <div className="flex items-center gap-2">
                <Avatar
                  shape="square"
                  size={30}
                  src={item.image_url ?? undefined}
                  icon={<Package size={14} />}
                />
                <div className="min-w-0 flex-1 leading-tight">
                  <div className="truncate text-sm">{item.name}</div>
                  {item.description && (
                    <div className="truncate text-xs text-gray-400">{item.description}</div>
                  )}
                </div>
                {item.track_inventory && item.stock != null && (
                  <span className="shrink-0 text-xs text-gray-400">Stock In Hand: {Number(item.stock)}</span>
                )}
              </div>
            );
          }}
          className="w-full"
        />
      ),
    },
    ...(usesBins && (bins?.length ?? 0) > 0
      ? ([
          {
            title: "Bin",
            key: "bin",
            width: 170,
            render: (_: unknown, row: LineRow) => (
              <Select
                value={row.bin_id ?? undefined}
                onChange={(value) =>
                  patchLine(row.key, {
                    bin_id: value ?? null,
                    lot_allocations: [],
                    serial_numbers: [],
                  })
                }
                options={(bins ?? []).map((bin) => ({
                  value: bin.id,
                  label: `${bin.code} · ${bin.name}`,
                }))}
                placeholder="Unassigned"
                disabled={!lineTracksInventory(row)}
                allowClear
                className="w-full"
              />
            ),
          },
        ] as ColumnsType<LineRow>)
      : []),
    ...(usesBins
      ? ([
          {
            title: "Tracking",
            key: "tracking",
            width: 150,
            render: (_: unknown, row: LineRow) => {
              const mode = lineTrackingMode(row);
              if (mode === "none") return <span className="text-gray-400">—</span>;
              const count =
                mode === "lot" ? row.lot_allocations.length : row.serial_numbers.length;
              return (
                <Button
                  size="small"
                  icon={<ScanLine size={14} />}
                  disabled={!row.product_id || !warehouseId}
                  onClick={() => setTrackingLineKey(row.key)}
                >
                  {count
                    ? mode === "lot"
                      ? `${count} ${count === 1 ? "lot" : "lots"}`
                      : `${count} serials`
                    : mode === "lot"
                      ? "Allocate lots"
                      : "Select serials"}
                </Button>
              );
            },
          },
        ] as ColumnsType<LineRow>)
      : []),
    {
      title: "Qty",
      key: "quantity",
      width: 100,
      render: (_, row) => (
        <InputNumber
          className="!w-full"
          min={0.001}
          value={row.quantity}
          onChange={(v) => patchLine(row.key, { quantity: v ?? 0 })}
        />
      ),
    },
    {
      title: "Rate",
      key: "unit_price",
      width: 130,
      render: (_, row) => (
        <InputNumber
          className="!w-full"
          min={0}
          prefix={currency}
          value={row.unit_price}
          onChange={(v) => patchLine(row.key, { unit_price: v ?? 0 })}
        />
      ),
    },
    {
      title: (
        <div className="flex items-center justify-between gap-2">
          <span>Discount</span>
          <Segmented
            size="small"
            value={discountMode}
            onChange={(v) => changeDiscountMode(v as DiscountType)}
            options={[
              { label: "%", value: "percent" },
              { label: "Fixed", value: "amount" },
            ]}
          />
        </div>
      ),
      key: "discount",
      width: 160,
      render: (_, row) => (
        <InputNumber
          className="!w-full"
          min={0}
          max={discountMode === "percent" ? 100 : undefined}
          value={row.discount_value}
          onChange={(v) => patchLine(row.key, { discount_value: v ?? 0 })}
          addonAfter={discountMode === "percent" ? "%" : currency}
        />
      ),
    },
    ...(showFbr
      ? ([
          {
            title: "Tax Rate",
            key: "sales_tax_rate",
            width: 110,
            render: (_, row) => <span className="text-gray-600">{row.fbr_rate ?? "—"}</span>,
          },
          {
            title: "Sales Tax",
            key: "sales_tax",
            width: 110,
            align: "right",
            render: (_, row) => {
              const taxable = row.quantity * row.unit_price - lineDiscount(row);
              return <span className="tabular-nums">{money(fbrSalesTax(row.fbr_rate, taxable, row.quantity))}</span>;
            },
          },
          {
            title: (
              <span className="inline-flex items-center gap-1">
                Further Tax
                <Tooltip title="Additional 3% tax charged when the buyer is not sales-tax registered (has no STRN).">
                  <Info size={13} className="text-gray-400" />
                </Tooltip>
              </span>
            ),
            key: "further_tax",
            width: 120,
            align: "right",
            render: (_, row) => {
              const taxable = row.quantity * row.unit_price - lineDiscount(row);
              return <span className="tabular-nums">{money(fbrFurtherTax(buyerRegistered, taxable))}</span>;
            },
          },
        ] as ColumnsType<LineRow>)
      : ([
          {
            title: "Tax",
            key: "tax",
            width: 150,
            render: (_, row) => (
              <Select
                value={row.tax_rate_id ?? undefined}
                onChange={(v) => patchLine(row.key, { tax_rate_id: v ?? null })}
                options={taxOptions}
                placeholder="No tax"
                allowClear
                onKeyDown={tabToNewRow(row)}
                className="w-full"
              />
            ),
          },
        ] as ColumnsType<LineRow>)),
    {
      title: "Amount",
      key: "amount",
      align: "right",
      width: 120,
      render: (_, row) => {
        const taxable = row.quantity * row.unit_price - lineDiscount(row);
        const tax = showFbr
          ? fbrSalesTax(row.fbr_rate, taxable, row.quantity) + fbrFurtherTax(buyerRegistered, taxable)
          : (taxable * rateOf(row.tax_rate_id)) / 100;
        return (
          <span className="tabular-nums">
            {money(taxable + tax)}
          </span>
        );
      },
    },
    {
      title: "",
      key: "remove",
      width: 48,
      align: "right",
      render: (_, row) => (
        <Button
          type="text"
          danger
          size="small"
          icon={<Trash2 size={14} />}
          disabled={lines.length === 1}
          onClick={() => removeLines([row.key])}
        />
      ),
    },
  ];

  const submit = async (values: FormValues) => {
    const clean = lines.filter((l) => l.description.trim() || l.product_id);
    if (!clean.length) {
      message.error("Add at least one line item");
      return;
    }
    const baselineNumber = isEdit ? document.number : nextNumber.data?.number;
    const typedNumber = values.number?.trim();
    const numberOverride = typedNumber && typedNumber !== baselineNumber ? typedNumber : undefined;
    const secondaryDate = config.secondaryDateField
      ? values[config.secondaryDateField]
      : undefined;
    const payload: DocumentInput = {
      party_id: values.party_id,
      ...(numberOverride ? { number: numberOverride } : {}),
      issue_date: values.issue_date.format("YYYY-MM-DD"),
      ...(config.secondaryDateField
        ? {
            [config.secondaryDateField]: secondaryDate
              ? secondaryDate.format("YYYY-MM-DD")
              : null,
          }
        : {}),
      reference: values.reference || null,
      warehouse_id: values.warehouse_id ?? null,
      notes: values.notes || null,
      terms: values.terms || null,
      shipping,
      adjustment,
      ...(showFbr
        ? {
            fbr_sale_origin: values.fbr_sale_origin || null,
            fbr_sale_destination: values.fbr_sale_destination || null,
            fbr_scenario_id: values.fbr_scenario_id || null,
          }
        : {}),
      ...(showFbrReason
        ? {
            fbr_reason: values.fbr_reason || null,
            fbr_reason_remarks:
              values.fbr_reason === FBR_REASON_OTHERS ? values.fbr_reason_remarks || null : null,
            ...(isSandbox ? { fbr_scenario_id: values.fbr_scenario_id || null } : {}),
          }
        : {}),
      lines: clean.map((l) => ({
        product_id: l.product_id,
        bin_id: usesBins ? l.bin_id : null,
        description: l.description.trim() || "Item",
        quantity: l.quantity,
        unit_price: l.unit_price,
        discount_type: l.discount_type,
        discount_value: l.discount_value,
        tax_rate_id: l.tax_rate_id,
        ...(usesBins && l.tracking_mode === "lot"
          ? { lot_allocations: l.lot_allocations }
          : {}),
        ...(usesBins && l.tracking_mode === "serial"
          ? { serial_numbers: l.serial_numbers }
          : {}),
      })),
    };
    try {
      const saved = isEdit
        ? await update.mutateAsync({ id: document.id, payload })
        : await create.mutateAsync(payload);
      if (saveModeRef.current === "finalize") {
        await finalize.mutateAsync(saved.id);
        message.success(`${config.labels.singular} finalized`);
      } else {
        message.success(`${config.labels.singular} ${isEdit ? "updated" : "created"}`);
      }
      router.push(`${config.basePath}/${saved.id}`);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  return (
    <Form<FormValues>
      form={form}
      layout="vertical"
      onFinish={submit}
      onValuesChange={(changed) => {
        if (showFbr && "party_id" in changed && !form.getFieldValue("fbr_sale_destination")) {
          const party = partyList.find((p) => p.id === changed.party_id);
          const province = party?.billing_address?.state;
          if (province) form.setFieldValue("fbr_sale_destination", province);
        }
      }}
      initialValues={{
        number: document?.number ?? undefined,
        party_id: document?.party_id ?? undefined,
        issue_date: document ? dayjs(document.issue_date) : dayjs(),
        due_date: document?.due_date ? dayjs(document.due_date) : null,
        expected_shipment_date: document?.expected_shipment_date
          ? dayjs(document.expected_shipment_date)
          : null,
        reference: document?.reference ?? undefined,
        warehouse_id: document?.warehouse_id ?? undefined,
        notes: document?.notes ?? undefined,
        terms: document?.terms ?? undefined,
        fbr_sale_origin: document?.fbr_sale_origin ?? org?.fbr_province ?? undefined,
        fbr_sale_destination: document?.fbr_sale_destination ?? undefined,
        fbr_scenario_id: document?.fbr_scenario_id ?? undefined,
        fbr_reason: document?.fbr_reason ?? undefined,
        fbr_reason_remarks: document?.fbr_reason_remarks ?? undefined,
      }}
      className="flex flex-col gap-6 pb-24"
    >
      <Typography.Title level={3} className="!mb-0">
        {isEdit ? `Edit ${document.number}` : config.labels.newAction}
      </Typography.Title>

      <Card className="border-gray-100">
        <div className="grid grid-cols-1 gap-x-6 md:grid-cols-3">
          <Form.Item name="number" label={`${config.labels.singular} No.`}>
            <Input placeholder="Auto-generated" />
          </Form.Item>
          <Form.Item
            name="party_id"
            label={config.labels.party}
            rules={[{ required: true, message: `${config.labels.party} is required` }]}
          >
            <Select
              options={partyOptions}
              placeholder={`Select ${config.labels.party.toLowerCase()}`}
              showSearch
              optionFilterProp="label"
              loading={parties.isLoading}
            />
          </Form.Item>
          <Form.Item
            name="issue_date"
            label={config.labels.dateLabel}
            rules={[{ required: true, message: `${config.labels.dateLabel} is required` }]}
          >
            <DatePicker className="!w-full" format="DD MMM YYYY" />
          </Form.Item>
          {config.secondaryDateField && (
            <Form.Item
              name={config.secondaryDateField}
              label={config.labels.secondaryDateLabel}
            >
              <DatePicker className="!w-full" format="DD MMM YYYY" />
            </Form.Item>
          )}
          <Form.Item name="reference" label={config.labels.referenceLabel}>
            <Input placeholder={config.labels.referencePlaceholder} />
          </Form.Item>
          <Form.Item name="warehouse_id" label="Warehouse" extra={config.labels.warehouseHint}>
            <Select
              options={(warehouses ?? []).map((w) => ({ value: w.id, label: w.name }))}
              placeholder="Default warehouse"
              allowClear
            />
          </Form.Item>
        </div>
      </Card>

      {showFbr && (
        <Card title="FBR e-Invoicing" className="border-gray-100">
          <div className="grid grid-cols-1 gap-x-6 md:grid-cols-3">
            <Form.Item name="fbr_sale_origin" label="Sale Origin" extra="Seller province of supply.">
              <Select options={PK_PROVINCES} placeholder="Province" showSearch optionFilterProp="label" allowClear />
            </Form.Item>
            <Form.Item name="fbr_sale_destination" label="Sale Destination" extra="Buyer province, defaults from the customer.">
              <Select options={PK_PROVINCES} placeholder="Province" showSearch optionFilterProp="label" allowClear />
            </Form.Item>
            {isSandbox && (
              <Form.Item name="fbr_scenario_id" label="Scenario" extra="Sandbox testing scenario.">
                <Select options={FBR_SCENARIOS} placeholder="Select scenario" showSearch optionFilterProp="label" allowClear />
              </Form.Item>
            )}
          </div>
        </Card>
      )}

      {showFbrReason && (
        <Card title="FBR e-Invoicing" className="border-gray-100">
          <div className="grid grid-cols-1 gap-x-6 md:grid-cols-2">
            <Form.Item
              name="fbr_reason"
              label="Reason"
              extra="Why this credit note is issued — required by FBR."
              rules={[{ required: true, message: "Select a reason" }]}
            >
              <Select options={FBR_REASONS} placeholder="Select reason" showSearch optionFilterProp="label" />
            </Form.Item>
            {isSandbox && (
              <Form.Item name="fbr_scenario_id" label="Scenario" extra="Sandbox testing scenario.">
                <Select options={FBR_SCENARIOS} placeholder="Select scenario" showSearch optionFilterProp="label" allowClear />
              </Form.Item>
            )}
            <Form.Item noStyle shouldUpdate={(prev, cur) => prev.fbr_reason !== cur.fbr_reason}>
              {({ getFieldValue }) =>
                getFieldValue("fbr_reason") === FBR_REASON_OTHERS ? (
                  <Form.Item
                    name="fbr_reason_remarks"
                    label="Remarks"
                    extra="Required when the reason is 'Others'."
                    rules={[{ required: true, message: "Add remarks for 'Others'" }]}
                  >
                    <Input placeholder="Describe the reason" maxLength={255} />
                  </Form.Item>
                ) : null
              }
            </Form.Item>
          </div>
        </Card>
      )}

      <Card title="Items" className="border-gray-100">
        <Table<LineRow>
          size="small"
          rowKey="key"
          columns={columns}
          dataSource={lines}
          pagination={false}
          scroll={{ x: 1150 }}
          rowSelection={{
            selectedRowKeys: selectedKeys,
            onChange: setSelectedKeys,
          }}
        />
        <div className="mt-3 flex items-center gap-3">
          <Button icon={<Plus size={16} />} onClick={() => addLine()}>
            Add line
          </Button>
          {selectedKeys.length > 0 && (
            <Button danger icon={<Trash2 size={16} />} onClick={() => removeLines(selectedKeys)}>
              Delete {selectedKeys.length} selected
            </Button>
          )}
        </div>

        <div className="mt-6 flex justify-end">
          <div className="w-full max-w-sm space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Subtotal</span>
              <span className="tabular-nums">{money(totals.subtotal)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Discount</span>
              <span className="tabular-nums">-{money(totals.discountTotal)}</span>
            </div>
            {showFbr && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Total Value Excluding Tax</span>
                <span className="tabular-nums">{money(totals.subtotal - totals.discountTotal)}</span>
              </div>
            )}
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">{showFbr ? "Sales Tax" : "Tax"}</span>
              <span className="tabular-nums">{money(totals.taxTotal)}</span>
            </div>
            {showFbr && totals.furtherTotal > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Further Tax</span>
                <span className="tabular-nums">{money(totals.furtherTotal)}</span>
              </div>
            )}
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Shipping</span>
              <InputNumber
                size="small"
                min={0}
                value={shipping}
                onChange={(v) => setShipping(v ?? 0)}
                className="!w-32"
              />
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Adjustment</span>
              <InputNumber
                size="small"
                value={adjustment}
                onChange={(v) => setAdjustment(v ?? 0)}
                className="!w-32"
              />
            </div>
            <div className="flex justify-between border-t border-gray-100 pt-2 text-base font-semibold">
              <span>Total</span>
              <span className="tabular-nums">{money(totals.total)}</span>
            </div>
          </div>
        </div>
      </Card>

      {(() => {
        const line = lines.find((candidate) => candidate.key === trackingLineKey);
        if (!line || line.product_id == null || line.tracking_mode === "none") return null;
        return (
          <LineTrackingModal
            open
            productId={line.product_id}
            productName={line.description || "Item"}
            trackingMode={line.tracking_mode}
            inbound={inboundStock}
            warehouseId={warehouseId}
            binId={line.bin_id}
            quantity={line.quantity}
            allocations={line.lot_allocations}
            serialNumbers={line.serial_numbers}
            onSave={(lotAllocations, serialNumbers) => {
              patchLine(line.key, {
                lot_allocations: lotAllocations,
                serial_numbers: serialNumbers,
              });
              setTrackingLineKey(null);
            }}
            onClose={() => setTrackingLineKey(null)}
          />
        );
      })()}

      <Card title="Notes & Terms" className="border-gray-100">
        <div className="grid grid-cols-1 gap-x-6 md:grid-cols-2">
          <Form.Item name="notes" label="Notes">
            <TextArea rows={3} placeholder="Notes" />
          </Form.Item>
          <Form.Item name="terms" label="Terms & conditions">
            <TextArea rows={3} placeholder="Payment terms" />
          </Form.Item>
        </div>
      </Card>

      <div className="sticky bottom-0 -mx-6 flex gap-3 border-t border-gray-100 bg-slate-50 px-6 py-3">
        <Dropdown.Button
          type="primary"
          className="!inline-flex !w-auto"
          loading={saving || finalize.isPending}
          onClick={() => {
            saveModeRef.current = "draft";
            form.submit();
          }}
          menu={{
            items: [{ key: "finalize", label: `Save & Finalize` }],
            onClick: ({ key }) => {
              if (key === "finalize") {
                saveModeRef.current = "finalize";
                form.submit();
              }
            },
          }}
        >
          {isEdit ? "Save" : "Save as Draft"}
        </Dropdown.Button>
        <Button onClick={() => router.push(backHref)}>Cancel</Button>
      </div>
    </Form>
  );
}
