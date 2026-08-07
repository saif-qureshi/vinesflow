"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type { Party, PartyInput, PartyRole, PartyType } from "@/types";

interface PartyPage {
  items: Party[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface PartyFilters {
  role?: PartyRole | null;
  search?: string;
  type?: PartyType | null;
  is_active?: boolean | null;
}

export function useParties(role?: PartyRole, filters: PartyFilters = {}, limit = 25) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useInfiniteQuery({
    queryKey: ["parties", orgId, role ?? "all", filters],
    queryFn: async ({ pageParam }) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (role) params.set("role", role);
      if (pageParam) params.set("cursor", pageParam as string);
      if (filters.search) params.set("search", filters.search);
      if (filters.type) params.set("type", filters.type);
      if (filters.is_active != null) params.set("is_active", String(filters.is_active));
      return (await api.get<PartyPage>(`/parties?${params.toString()}`)).data;
    },
    initialPageParam: null as string | null,
    getNextPageParam: (last) => (last.has_more ? last.next_cursor : undefined),
    enabled: !!token && !!orgId,
  });
}

export function useParty(id: number | null) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["party", orgId, id],
    queryFn: async () => (await api.get<Party>(`/parties/${id}`)).data,
    enabled: !!token && !!orgId && !!id,
  });
}

function useInvalidate() {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return () => qc.invalidateQueries({ queryKey: ["parties", orgId] });
}

export function useCreateParty() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: PartyInput) => api.post<Party>("/parties", payload),
    onSuccess: invalidate,
  });
}

export function useUpdateParty() {
  const invalidate = useInvalidate();
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useMutation({
    mutationFn: (vars: { id: number; payload: Partial<PartyInput> }) =>
      api.patch<Party>(`/parties/${vars.id}`, vars.payload),
    onSuccess: (_res, vars) => {
      invalidate();
      qc.invalidateQueries({ queryKey: ["party", orgId, vars.id] });
    },
  });
}

export function useDeleteParty() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/parties/${id}`),
    onSuccess: invalidate,
  });
}

export function useSetPartyOpeningBalance() {
  const invalidate = useInvalidate();
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useMutation({
    mutationFn: (vars: { partyId: number; amount: number; asOf?: string }) =>
      api.put(`/accounting/parties/${vars.partyId}/opening-balance`, {
        amount: vars.amount,
        as_of: vars.asOf ?? new Date().toISOString().slice(0, 10),
      }),
    onSuccess: (_res, vars) => {
      invalidate();
      qc.invalidateQueries({ queryKey: ["party", orgId, vars.partyId] });
      qc.invalidateQueries({ queryKey: ["reports"] });
    },
  });
}
