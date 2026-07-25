"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type { InventoryItem, ItemStock, StockMovement } from "@/types";

interface InventoryPage {
  items: InventoryItem[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface InventoryFilters {
  search?: string;
  location_id?: number | null;
  low_stock?: boolean | null;
}

export function useInventory(filters: InventoryFilters = {}, limit = 25) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useInfiniteQuery({
    queryKey: ["inventory", orgId, filters],
    queryFn: async ({ pageParam }) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (pageParam) params.set("cursor", pageParam as string);
      if (filters.search) params.set("search", filters.search);
      if (filters.location_id != null) params.set("location_id", String(filters.location_id));
      if (filters.low_stock) params.set("low_stock", "true");
      return (await api.get<InventoryPage>(`/inventory?${params.toString()}`)).data;
    },
    initialPageParam: null as string | null,
    getNextPageParam: (last) => (last.has_more ? last.next_cursor : undefined),
    enabled: !!token && !!orgId,
  });
}

export function useItemStock(productId: number | null) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["item-stock", orgId, productId],
    queryFn: async () => (await api.get<ItemStock>(`/inventory/${productId}/stock`)).data,
    enabled: !!token && !!orgId && !!productId,
  });
}

export function useOnHand(productId: number | null, locationId: number | null | undefined) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["on-hand", orgId, productId, locationId ?? null],
    queryFn: async () =>
      (await api.get<{ quantity: string }>(`/inventory/${productId}/on-hand?location_id=${locationId}`))
        .data.quantity,
    enabled: !!token && !!orgId && !!productId && !!locationId,
  });
}

export function useItemMovements(productId: number | null, limit = 50) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["item-movements", orgId, productId],
    queryFn: async () =>
      (await api.get<{ items: StockMovement[] }>(`/inventory/${productId}/movements?limit=${limit}`))
        .data.items,
    enabled: !!token && !!orgId && !!productId,
  });
}

interface AdjustInput {
  product_id: number;
  location_id: number;
  qty_delta: number;
  reason?: string | null;
  note?: string | null;
}

interface TransferInput {
  product_id: number;
  from_location_id: number;
  to_location_id: number;
  quantity: number;
  note?: string | null;
}

function useInvalidate() {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return (productId?: number) => {
    qc.invalidateQueries({ queryKey: ["inventory", orgId] });
    if (productId) {
      qc.invalidateQueries({ queryKey: ["item-stock", orgId, productId] });
      qc.invalidateQueries({ queryKey: ["item-movements", orgId, productId] });
    }
  };
}

export function useAdjustStock() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: AdjustInput) => api.post("/inventory/adjust", payload),
    onSuccess: (_r, vars) => invalidate(vars.product_id),
  });
}

export function useTransferStock() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: TransferInput) => api.post("/inventory/transfer", payload),
    onSuccess: (_r, vars) => invalidate(vars.product_id),
  });
}
