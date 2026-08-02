"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type { SerialUnit, StockLot } from "@/types";

export function useLots(
  productId?: number | null,
  locationId?: number | null,
  binId?: number | null,
  exactBin = false,
) {
  const token = useSessionStore((state) => state.accessToken);
  const orgId = useSessionStore((state) => state.currentOrgId);
  return useQuery({
    queryKey: ["stock-lots", orgId, productId, locationId, binId, exactBin],
    queryFn: async () =>
      (
        await api.get<StockLot[]>("/inventory/lots", {
          params: {
            product_id: productId,
            ...(locationId != null ? { location_id: locationId } : {}),
            ...(binId != null ? { bin_id: binId } : {}),
            ...(exactBin && binId == null ? { unbinned: true } : {}),
          },
        })
      ).data,
    enabled: !!token && !!orgId && productId != null,
  });
}

export function useSerialUnits(
  productId?: number | null,
  locationId?: number | null,
  binId?: number | null,
  inStockOnly = false,
  exactBin = false,
) {
  const token = useSessionStore((state) => state.accessToken);
  const orgId = useSessionStore((state) => state.currentOrgId);
  return useQuery({
    queryKey: ["serial-units", orgId, productId, locationId, binId, inStockOnly, exactBin],
    queryFn: async () =>
      (
        await api.get<SerialUnit[]>("/inventory/serials", {
          params: {
            product_id: productId,
            ...(locationId != null ? { location_id: locationId } : {}),
            ...(binId != null ? { bin_id: binId } : {}),
            ...(exactBin && binId == null ? { unbinned: true } : {}),
            ...(inStockOnly ? { status: "in_stock" } : {}),
          },
        })
      ).data,
    enabled: !!token && !!orgId && productId != null,
  });
}
