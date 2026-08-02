"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type { Bin, BinInput } from "@/types";

export function useBins(locationId?: number | null, activeOnly = false, enabled = true) {
  const token = useSessionStore((state) => state.accessToken);
  const orgId = useSessionStore((state) => state.currentOrgId);
  return useQuery({
    queryKey: ["bins", orgId, locationId ?? null, activeOnly],
    queryFn: async () =>
      (
        await api.get<Bin[]>("/inventory/bins", {
          params: {
            ...(locationId != null ? { location_id: locationId } : {}),
            ...(activeOnly ? { active_only: true } : {}),
          },
        })
      ).data,
    enabled: enabled && !!token && !!orgId,
  });
}

function useInvalidateBins() {
  const queryClient = useQueryClient();
  const orgId = useSessionStore((state) => state.currentOrgId);
  return () => queryClient.invalidateQueries({ queryKey: ["bins", orgId] });
}

export function useCreateBin() {
  const invalidate = useInvalidateBins();
  return useMutation({
    mutationFn: (payload: BinInput) => api.post<Bin>("/inventory/bins", payload),
    onSuccess: invalidate,
  });
}

export function useUpdateBin() {
  const invalidate = useInvalidateBins();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<BinInput> }) =>
      api.patch<Bin>(`/inventory/bins/${id}`, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteBin() {
  const invalidate = useInvalidateBins();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/inventory/bins/${id}`),
    onSuccess: invalidate,
  });
}
