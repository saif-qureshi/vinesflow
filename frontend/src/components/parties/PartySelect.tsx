"use client";

import { useEffect, useMemo, useState } from "react";

import { Select } from "@/components/ui";
import { useParties } from "@/hooks/useParties";
import type { PartyRole } from "@/types";

interface PartySelectProps {
  role?: PartyRole;
  value?: number;
  onChange?: (value: number) => void;
  placeholder?: string;
  /** The already-chosen party, so its name still shows when it falls outside
   *  the current search results. */
  selected?: { id: number; name: string } | null;
  disabled?: boolean;
  className?: string;
}

export function PartySelect({
  role,
  value,
  onChange,
  placeholder,
  selected,
  disabled,
  className = "w-full",
}: PartySelectProps) {
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setSearch(input.trim()), 300);
    return () => clearTimeout(timer);
  }, [input]);

  const query = useParties(role, search ? { search } : {});

  const options = useMemo(() => {
    const rows = query.data?.pages.flatMap((page) => page.items) ?? [];
    const found = rows.map((party) => ({ value: party.id, label: party.name }));
    if (selected && !rows.some((party) => party.id === selected.id)) {
      found.unshift({ value: selected.id, label: selected.name });
    }
    return found;
  }, [query.data, selected]);

  return (
    <Select
      value={value}
      onChange={onChange}
      options={options}
      placeholder={placeholder}
      showSearch
      filterOption={false}
      onSearch={setInput}
      onPopupScroll={(e) => {
        const el = e.currentTarget;
        const atEnd = el.scrollTop + el.offsetHeight >= el.scrollHeight - 24;
        if (atEnd && query.hasNextPage && !query.isFetchingNextPage) {
          query.fetchNextPage();
        }
      }}
      loading={query.isFetching}
      disabled={disabled}
      className={className}
      notFoundContent={query.isFetching ? "Searching…" : "No matches"}
    />
  );
}
