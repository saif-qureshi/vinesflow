"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { InputNumber, Radio, Segmented, Switch } from "antd";
import { X } from "lucide-react";

import { App, Button, Card, Form, Input, Select, TextArea, Typography } from "@/components/ui";
import { Uploader } from "@/components/ui/Uploader";
import { FbrReferenceSelect } from "@/components/fbr/FbrReferenceSelect";
import { FbrSroItemSelect } from "@/components/fbr/FbrSroItemSelect";
import { FbrUomSelect } from "@/components/fbr/FbrUomSelect";
import { useFbrReference } from "@/hooks/useFbr";
import { useCategories } from "@/hooks/useCategories";
import { useNamedList } from "@/hooks/useMasterData";
import { useUoms } from "@/hooks/useUoms";
import { useCreateProduct, useUpdateProduct } from "@/hooks/useProducts";
import { useCurrency } from "@/hooks/useCurrency";
import { useSession } from "@/hooks/useSession";
import { apiErrorMessage } from "@/lib/api";
import type { Product, ProductInput, UploadedFile, VariantAttribute } from "@/types";
import { VariantsBuilder } from "./VariantsBuilder";
import { cartesian, variantSig, type VariantOverride } from "./variants";

interface FormValues {
  name: string;
  nature: "good" | "service";
  type: "single" | "variable";
  category_id?: number | null;
  brand_id?: number | null;
  manufacturer_id?: number | null;
  uom_id?: number | null;
  sku?: string;
  barcode?: string;
  description?: string;
  sale_price?: number | null;
  purchase_price?: number | null;
  track_inventory: boolean;
  tracking_mode: "none" | "lot" | "serial";
  reorder_point?: number | null;
  hs_code?: string;
  uom_code?: string;
  sale_type_code?: string;
  tax_rate_code?: string;
  sro_schedule_code?: string;
  sro_item_serial?: string;
}

export function ItemForm({ product }: { product?: Product }) {
  const router = useRouter();
  const { message } = App.useApp();
  const { currency } = useCurrency();
  const { currentMembership } = useSession();
  const categories = useCategories();
  const brands = useNamedList("brands", true);
  const manufacturers = useNamedList("manufacturers", true);
  const uoms = useUoms();
  const create = useCreateProduct();
  const update = useUpdateProduct();
  const [form] = Form.useForm<FormValues>();
  const fbrEnabled = currentMembership?.organization.fbr_enabled ?? false;
  const saleType = Form.useWatch("sale_type_code", form);
  const taxRate = Form.useWatch("tax_rate_code", form);
  const sroSchedule = Form.useWatch("sro_schedule_code", form);
  const hsCode = Form.useWatch("hs_code", form);

  const [media, setMedia] = useState<UploadedFile[]>(
    () => product?.media.map((m) => ({ storage_key: m.storage_key, url: m.url })) ?? [],
  );
  const [attributes, setAttributes] = useState<VariantAttribute[]>(
    () => product?.variant_attributes ?? [],
  );
  const [overrides, setOverrides] = useState<Record<string, VariantOverride>>(() => {
    const ov: Record<string, VariantOverride> = {};
    for (const v of product?.variants ?? []) {
      const options = Object.fromEntries(v.values.map((val) => [val.attribute_name, val.value]));
      ov[variantSig(options)] = {
        id: v.id,
        sku: v.sku ?? undefined,
        sale_price: v.sale_price,
        purchase_price: v.purchase_price,
      };
    }
    return ov;
  });
  const [excluded, setExcluded] = useState<Set<string>>(() => {
    if (!product) return new Set();
    const present = new Set(
      product.variants.map((v) =>
        variantSig(Object.fromEntries(v.values.map((val) => [val.attribute_name, val.value]))),
      ),
    );
    return new Set(
      cartesian(product.variant_attributes)
        .map(variantSig)
        .filter((sig) => !present.has(sig)),
    );
  });

  const isEdit = !!product;
  const isVariable = Form.useWatch("type", form) === "variable";
  const natureValue = Form.useWatch("nature", form);
  const trackInventory = Form.useWatch("track_inventory", form);
  const skuValue = Form.useWatch("sku", form);
  const nameValue = Form.useWatch("name", form);
  const saving = create.isPending || update.isPending;
  const backHref = isEdit ? `/items/${product.id}` : "/items";

  const saleTypes = useFbrReference("sale_type", { enabled: fbrEnabled && !isEdit });
  const defaultSaleType = useMemo(
    () => saleTypes.data?.find((s) => (s.description ?? "").toLowerCase().includes("(default)"))?.code,
    [saleTypes.data],
  );
  const defaultRates = useFbrReference("tax_rate", {
    parent: defaultSaleType,
    enabled: fbrEnabled && !isEdit && !!defaultSaleType,
  });

  useEffect(() => {
    if (isEdit || !fbrEnabled || !defaultSaleType) return;
    if (!form.getFieldValue("sale_type_code")) {
      form.setFieldValue("sale_type_code", defaultSaleType);
    }
    if (
      form.getFieldValue("sale_type_code") === defaultSaleType &&
      !form.getFieldValue("tax_rate_code") &&
      defaultRates.data?.length === 1
    ) {
      form.setFieldValue("tax_rate_code", defaultRates.data[0].code);
    }
  }, [defaultSaleType, defaultRates.data, isEdit, fbrEnabled, form]);

  useEffect(() => {
    if (!product) return;
    form.setFieldsValue({
      name: product.name,
      nature: product.nature,
      type: product.type,
      category_id: product.category?.id,
      brand_id: product.brand?.id,
      manufacturer_id: product.manufacturer?.id,
      uom_id: product.uom?.id,
      sku: product.sku ?? undefined,
      barcode: product.barcode ?? undefined,
      description: product.description ?? undefined,
      sale_price: product.sale_price ?? undefined,
      purchase_price: product.purchase_price ?? undefined,
      track_inventory: product.track_inventory,
      tracking_mode: product.tracking_mode,
      reorder_point: product.reorder_point ?? undefined,
      hs_code: product.hs_code ?? undefined,
      uom_code: product.uom_code ?? undefined,
      sale_type_code: product.sale_type_code ?? undefined,
      tax_rate_code: product.tax_rate_code ?? undefined,
      sro_schedule_code: product.sro_schedule_code ?? undefined,
      sro_item_serial: product.sro_item_serial ?? undefined,
    });
  }, [product, form]);

  const submit = async (values: FormValues) => {
    const variable = values.type === "variable";
    const cleanAttrs = attributes.filter((a) => a.name.trim() && a.options.length);
    const payload: ProductInput = {
      ...values,
      tracking_mode: values.track_inventory ? values.tracking_mode : "none",
      media: media.map((m, i) => ({ storage_key: m.storage_key, sort_order: i })),
      variant_attributes: variable ? cleanAttrs : [],
      variants: variable
        ? cartesian(cleanAttrs)
            .filter((options) => !excluded.has(variantSig(options)))
            .map((options) => {
              const o = overrides[variantSig(options)] ?? {};
              return {
                id: o.id,
                options,
                sku: o.sku || undefined,
                sale_price: o.sale_price ?? undefined,
                purchase_price: o.purchase_price ?? undefined,
              };
            })
        : [],
    };
    try {
      if (isEdit) await update.mutateAsync({ id: product.id, payload });
      else await create.mutateAsync(payload);
      message.success(isEdit ? "Item updated" : "Item created");
      router.push(backHref);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const categoryOptions = (categories.data ?? []).map((c) => ({ value: c.id, label: c.name }));
  const brandOptions = (brands.data ?? []).map((b) => ({ value: b.id, label: b.name }));
  const manufacturerOptions = (manufacturers.data ?? []).map((m) => ({ value: m.id, label: m.name }));
  const uomOptions = (uoms.data ?? []).map((u) => ({ value: u.id, label: `${u.name} (${u.symbol})` }));

  return (
    <Form<FormValues>
      form={form}
      layout="vertical"
      onFinish={submit}
      onValuesChange={(changed) => {
        if ("sale_type_code" in changed)
          form.setFieldsValue({ tax_rate_code: undefined, sro_schedule_code: undefined, sro_item_serial: undefined });
        if ("tax_rate_code" in changed)
          form.setFieldsValue({ sro_schedule_code: undefined, sro_item_serial: undefined });
        if ("sro_schedule_code" in changed) form.setFieldValue("sro_item_serial", undefined);
        if ("hs_code" in changed) form.setFieldValue("uom_code", undefined);
        if ("track_inventory" in changed && !changed.track_inventory) {
          form.setFieldValue("tracking_mode", "none");
        }
      }}
      initialValues={{
        nature: "good",
        type: "single",
        track_inventory: false,
        tracking_mode: "none",
      }}
      className="flex flex-col gap-6 pb-24"
    >
      <div className="flex items-center justify-between">
        <Typography.Title level={3} className="!mb-0">
          {isEdit ? "Edit Item" : "New Item"}
        </Typography.Title>
        <Button type="text" icon={<X size={18} />} onClick={() => router.push(backHref)} />
      </div>

      <Card className="border-gray-100">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-1 lg:col-span-2">
            <Form.Item name="name" label="Name" rules={[{ required: true, message: "Name is required" }]}>
              <Input placeholder="e.g. iPhone 16" />
            </Form.Item>
            <Form.Item name="nature" label="Type">
              <Radio.Group
                options={[
                  { label: "Goods", value: "good" },
                  { label: "Service", value: "service" },
                ]}
              />
            </Form.Item>
            <div className="grid grid-cols-1 gap-x-6 md:grid-cols-2">
              <Form.Item name="category_id" label="Category">
                <Select options={categoryOptions} placeholder="Select category" allowClear showSearch optionFilterProp="label" loading={categories.isLoading} />
              </Form.Item>
              <Form.Item
                name="uom_id"
                label="Unit"
                dependencies={["nature"]}
                rules={
                  natureValue === "good"
                    ? [{ required: true, message: "Unit is required for goods" }]
                    : []
                }
              >
                <Select options={uomOptions} placeholder="Select unit" allowClear showSearch optionFilterProp="label" loading={uoms.isLoading} />
              </Form.Item>
              <Form.Item name="brand_id" label="Brand">
                <Select options={brandOptions} placeholder="Select brand" allowClear showSearch optionFilterProp="label" loading={brands.isLoading} />
              </Form.Item>
              <Form.Item name="manufacturer_id" label="Manufacturer">
                <Select options={manufacturerOptions} placeholder="Select manufacturer" allowClear showSearch optionFilterProp="label" loading={manufacturers.isLoading} />
              </Form.Item>
              <Form.Item name="sku" label="SKU">
                <Input placeholder="Stock keeping unit" />
              </Form.Item>
              <Form.Item name="barcode" label="Barcode">
                <Input placeholder="UPC / EAN" />
              </Form.Item>
            </div>
          </div>
          <div>
            <div className="mb-2 text-sm font-medium">Images</div>
            <Uploader value={media} onChange={setMedia} accept="image/*" maxCount={15} maxSizeMB={5} />
          </div>
        </div>
      </Card>

      <Card title="Item Details" className="border-gray-100">
        <Form.Item name="type" label="Item Type">
          <Segmented
            options={[
              { label: "Single Item", value: "single" },
              { label: "Contains Variants", value: "variable" },
            ]}
          />
        </Form.Item>

        {isVariable ? (
          <VariantsBuilder
            attributes={attributes}
            setAttributes={setAttributes}
            overrides={overrides}
            setOverrides={setOverrides}
            currency={currency}
            baseSku={skuValue ?? ""}
            baseName={nameValue ?? ""}
            excluded={excluded}
            onRemove={(sig) =>
              setExcluded((prev) => {
                const next = new Set(prev);
                next.add(sig);
                return next;
              })
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-x-6 md:grid-cols-2">
            <Form.Item name="sale_price" label="Sale Price">
              <InputNumber className="!w-full" min={0} prefix={currency} placeholder="0.00" />
            </Form.Item>
            <Form.Item name="purchase_price" label="Purchase Price">
              <InputNumber className="!w-full" min={0} prefix={currency} placeholder="0.00" />
            </Form.Item>
          </div>
        )}
      </Card>

      <Card title="Inventory" className="border-gray-100">
        <div className="grid grid-cols-1 gap-x-6 md:grid-cols-2">
          <Form.Item name="track_inventory" label="Track inventory" valuePropName="checked" extra="Cannot be changed once transactions exist.">
            <Switch />
          </Form.Item>
          <Form.Item
            name="tracking_mode"
            label="Traceability"
            extra="Cannot be changed once inventory transactions exist."
          >
            <Select
              disabled={!trackInventory || natureValue !== "good"}
              options={[
                { value: "none", label: "No lot or serial tracking" },
                { value: "lot", label: "Batch / lot with expiry" },
                { value: "serial", label: "Serial number" },
              ]}
            />
          </Form.Item>
          <Form.Item name="reorder_point" label="Reorder point">
            <InputNumber className="!w-full" min={0} placeholder="e.g. 10" />
          </Form.Item>
        </div>
      </Card>

      {fbrEnabled && (
        <Card title="FBR e-Invoicing" className="border-gray-100">
          <div className="grid grid-cols-1 gap-x-6 md:grid-cols-2">
            <Form.Item name="hs_code" label="HS Code" extra="Customs tariff code reported to FBR.">
              <FbrReferenceSelect type="hs_code" placeholder="Search HS code or description" />
            </Form.Item>
            <Form.Item
              name="uom_code"
              label="Unit of Measure (FBR)"
              dependencies={["hs_code"]}
              extra={hsCode ? "Units allowed for the selected HS code." : "Pick an HS code to narrow the units."}
            >
              <FbrUomSelect hsCode={hsCode} placeholder="Select FBR unit" />
            </Form.Item>
            <Form.Item name="sale_type_code" label="Sale Type">
              <FbrReferenceSelect type="sale_type" placeholder="Select sale type" />
            </Form.Item>
            <Form.Item name="tax_rate_code" label="Tax Rate" dependencies={["sale_type_code"]}>
              <FbrReferenceSelect
                type="tax_rate"
                parent={saleType}
                placeholder={saleType ? "Select tax rate" : "Pick a sale type first"}
                disabled={!saleType}
              />
            </Form.Item>
            <Form.Item
              name="sro_schedule_code"
              label="SRO Schedule"
              dependencies={["tax_rate_code"]}
              extra="Required for exempt, reduced-rate, or SRO-based items."
            >
              <FbrReferenceSelect
                type="sro_schedule"
                parent={taxRate}
                placeholder={taxRate ? "Select SRO schedule" : "Pick a tax rate first"}
                disabled={!taxRate}
              />
            </Form.Item>
            <Form.Item name="sro_item_serial" label="SRO Item Serial" dependencies={["sro_schedule_code"]}>
              <FbrSroItemSelect
                sroId={sroSchedule}
                placeholder={sroSchedule ? "Select serial number" : "Pick an SRO schedule first"}
                disabled={!sroSchedule}
              />
            </Form.Item>
          </div>
        </Card>
      )}

      <Card title="Description" className="border-gray-100">
        <Form.Item name="description" noStyle>
          <TextArea rows={3} placeholder="Describe this item" />
        </Form.Item>
      </Card>

      <div className="sticky bottom-0 -mx-6 flex gap-3 border-t border-gray-100 bg-slate-50 px-6 py-3">
        <Button type="primary" htmlType="submit" loading={saving}>
          {isEdit ? "Save" : "Create Item"}
        </Button>
        <Button onClick={() => router.push(backHref)}>Cancel</Button>
      </div>
    </Form>
  );
}
