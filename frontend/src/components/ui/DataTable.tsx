"use client";

import { useEffect, useState } from "react";
import { Button, Input, Table } from "antd";
import type { TableProps } from "antd";
import { Search } from "lucide-react";

interface DataTableProps<T> extends TableProps<T> {
  onRowClick?: (row: T) => void;
  // Cursor ("load more") pagination.
  hasMore?: boolean;
  onLoadMore?: () => void;
  loadingMore?: boolean;
  // Toolbar: debounced search + a slot for filter controls.
  searchable?: boolean;
  searchPlaceholder?: string;
  onSearch?: (value: string) => void;
  toolbar?: React.ReactNode;
}

export function DataTable<T extends object>({
  onRowClick,
  hasMore,
  onLoadMore,
  loadingMore,
  searchable,
  searchPlaceholder = "Search…",
  onSearch,
  toolbar,
  scroll,
  ...props
}: DataTableProps<T>) {
  const [q, setQ] = useState("");

  useEffect(() => {
    if (!onSearch) return;
    const t = setTimeout(() => onSearch(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q, onSearch]);

  const hasToolbar = searchable || toolbar;

  return (
    <div className="overflow-hidden rounded-xl border border-gray-100 bg-white">
      {hasToolbar && (
        <div className="flex flex-wrap items-center gap-3 border-b border-gray-100 p-3 sm:justify-end">
          {toolbar}
          {searchable && (
            <Input
              prefix={<Search size={16} className="text-gray-400" />}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={searchPlaceholder}
              allowClear
              className="!w-full sm:!w-72"
            />
          )}
        </div>
      )}
      <Table<T>
        rowKey="id"
        pagination={false}
        scroll={scroll ?? { x: "max-content" }}
        onRow={
          onRowClick
            ? (row) => ({ onClick: () => onRowClick(row), style: { cursor: "pointer" } })
            : undefined
        }
        {...props}
      />
      {hasMore && (
        <div className="flex justify-center border-t border-gray-100 p-3">
          <Button onClick={onLoadMore} loading={loadingMore}>
            Load more
          </Button>
        </div>
      )}
    </div>
  );
}
