"use client";

import { useMemo, useRef, useState } from "react";

import { Select } from "@/components/ui";
import { FbrReferenceType, useFbrReference } from "@/hooks/useFbr";

const short = (s: string | null, n = 70) => (s && s.length > n ? `${s.slice(0, n)}…` : s ?? "");

interface Props {
  type: FbrReferenceType;
  parent?: string;
  value?: string;
  onChange?: (value?: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function FbrReferenceSelect({ type, parent, value, onChange, placeholder, disabled }: Props) {
  const serverSearch = type === "hs_code";
  const [search, setSearch] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const needsParent = type === "tax_rate" || type === "sro_schedule";
  const query = useFbrReference(type, {
    parent,
    search: serverSearch ? search : undefined,
    enabled: !disabled && (!needsParent || !!parent),
  });

  const options = useMemo(() => {
    const opts = (query.data ?? []).map((r) => ({
      value: r.code,
      label: type === "hs_code" ? `${r.code} — ${short(r.description)}` : short(r.description) || r.code,
    }));
    if (value && !opts.some((o) => o.value === value)) opts.unshift({ value, label: value });
    return opts;
  }, [query.data, value, type]);

  const onSearch = (term: string) => {
    if (!serverSearch) return;
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setSearch(term), 300);
  };

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
      filterOption={serverSearch ? false : undefined}
      onSearch={serverSearch ? onSearch : undefined}
      notFoundContent={serverSearch && !search ? "Type to search" : undefined}
      className="!w-full"
    />
  );
}
