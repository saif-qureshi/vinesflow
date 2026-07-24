"use client";

import { Input, Select } from "antd";

import { PK_PROVINCES, isPakistan } from "@/lib/provinces";
import type { Address } from "@/types";
import { PhoneField } from "./PhoneField";

const FIELDS: [keyof Address, string][] = [
  ["attention", "Attention"],
  ["line1", "Address line 1"],
  ["line2", "Address line 2"],
  ["city", "City"],
  ["state", "State / Province"],
  ["postal_code", "Postal code"],
  ["country", "Country"],
  ["phone", "Phone"],
];

interface AddressFieldProps {
  value?: Address;
  onChange?: (value: Address) => void;
  disabled?: boolean;
}

export function AddressField({ value = {}, onChange, disabled }: AddressFieldProps) {
  const set = (key: keyof Address, v: string) => onChange?.({ ...value, [key]: v });
  const pk = isPakistan(value.country);

  return (
    <div className="grid grid-cols-1 gap-x-6 gap-y-3 md:grid-cols-2">
      {FIELDS.map(([key, label]) => (
        <div key={key}>
          <div className="mb-1 text-sm text-gray-600">{label}</div>
          {key === "phone" ? (
            <PhoneField value={value[key] ?? undefined} onChange={(v) => set(key, v)} placeholder={label} />
          ) : key === "state" && pk ? (
            <Select
              value={value.state || undefined}
              onChange={(v) => set("state", v ?? "")}
              options={PK_PROVINCES}
              placeholder="Province"
              showSearch
              optionFilterProp="label"
              allowClear
              disabled={disabled}
              className="!w-full"
            />
          ) : (
            <Input
              value={value[key] ?? ""}
              onChange={(e) => set(key, e.target.value)}
              placeholder={label}
              disabled={disabled}
            />
          )}
        </div>
      ))}
    </div>
  );
}
