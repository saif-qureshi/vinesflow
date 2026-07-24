"use client";

import { useMemo } from "react";

import { Select } from "@/components/ui";
import { useFbrSroItems } from "@/hooks/useFbr";

interface Props {
  sroId?: string;
  value?: string;
  onChange?: (value?: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function FbrSroItemSelect({ sroId, value, onChange, placeholder, disabled }: Props) {
  const query = useFbrSroItems(sroId);

  const options = useMemo(() => {
    const opts = (query.data ?? []).map((r) => ({ value: r.code, label: r.description || r.code }));
    if (value && !opts.some((o) => o.value === value)) opts.unshift({ value, label: value });
    return opts;
  }, [query.data, value]);

  return (
    <Select
      showSearch
      allowClear
      value={value}
      onChange={(v) => onChange?.(v ?? undefined)}
      options={options}
      placeholder={placeholder}
      disabled={disabled}
      loading={query.isFetching}
      optionFilterProp="label"
      className="!w-full"
    />
  );
}
