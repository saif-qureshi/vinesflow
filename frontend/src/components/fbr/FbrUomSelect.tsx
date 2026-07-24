"use client";

import { useMemo } from "react";

import { Select } from "@/components/ui";
import { useFbrHsUom, useFbrReference } from "@/hooks/useFbr";

interface Props {
  hsCode?: string;
  value?: string;
  onChange?: (value?: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function FbrUomSelect({ hsCode, value, onChange, placeholder, disabled }: Props) {
  const hsUom = useFbrHsUom(hsCode);
  const restricted = !!hsCode && (hsUom.data?.length ?? 0) > 0;
  const all = useFbrReference("uom", { enabled: !disabled && !restricted });

  const source = restricted ? hsUom.data : all.data;
  const loading = hsUom.isFetching || all.isFetching;

  const options = useMemo(() => {
    const opts = (source ?? []).map((r) => ({ value: r.code, label: r.description || r.code }));
    if (value && !opts.some((o) => o.value === value)) opts.unshift({ value, label: value });
    return opts;
  }, [source, value]);

  return (
    <Select
      showSearch
      allowClear
      value={value}
      onChange={(v) => onChange?.(v ?? undefined)}
      options={options}
      placeholder={placeholder}
      disabled={disabled}
      loading={loading}
      optionFilterProp="label"
      className="!w-full"
    />
  );
}
