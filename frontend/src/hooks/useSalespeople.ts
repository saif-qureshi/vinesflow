"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type { Salesperson, SalespersonInput } from "@/types";

export function useSalespeople(activeOnly = false) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["salespeople", orgId],
    queryFn: async () => (await api.get<Salesperson[]>("/salespeople")).data,
    enabled: !!token && !!orgId,
    select: activeOnly ? (rows) => rows.filter((row) => row.is_active) : undefined,
  });
}

function useInvalidate() {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return () => qc.invalidateQueries({ queryKey: ["salespeople", orgId] });
}

export function useCreateSalesperson() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: SalespersonInput) => api.post<Salesperson>("/salespeople", payload),
    onSuccess: invalidate,
  });
}

export function useUpdateSalesperson() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (vars: { id: number; payload: SalespersonInput }) =>
      api.patch<Salesperson>(`/salespeople/${vars.id}`, vars.payload),
    onSuccess: invalidate,
  });
}

export function useDeleteSalesperson() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/salespeople/${id}`),
    onSuccess: invalidate,
  });
}
