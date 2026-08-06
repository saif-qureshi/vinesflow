"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type {
  DocumentInput,
  DocumentRecord,
  DocumentStatus,
  DocumentSummary,
  SellableItem,
  TaxRate,
} from "@/types";

interface DocumentPage {
  items: DocumentSummary[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface DocumentFilters {
  search?: string;
  status?: DocumentStatus | null;
  payment_status?: string | null;
  party_id?: number | null;
}

export function useDocumentList(apiPath: string, filters: DocumentFilters = {}, limit = 25) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useInfiniteQuery({
    queryKey: [apiPath, orgId, filters],
    queryFn: async ({ pageParam }) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (pageParam) params.set("cursor", pageParam as string);
      if (filters.search) params.set("search", filters.search);
      if (filters.status) params.set("status", filters.status);
      if (filters.payment_status) params.set("payment_status", filters.payment_status);
      if (filters.party_id != null) params.set("party_id", String(filters.party_id));
      return (await api.get<DocumentPage>(`/${apiPath}?${params.toString()}`)).data;
    },
    initialPageParam: null as string | null,
    getNextPageParam: (last) => (last.has_more ? last.next_cursor : undefined),
    enabled: !!token && !!orgId,
  });
}

export function useDocument(apiPath: string, id: number | null) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: [apiPath, "one", orgId, id],
    queryFn: async () => (await api.get<DocumentRecord>(`/${apiPath}/${id}`)).data,
    enabled: !!token && !!orgId && !!id,
  });
}

function useInvalidate(apiPath: string) {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return (id?: number) => {
    qc.invalidateQueries({ queryKey: [apiPath, orgId] });
    if (id) qc.invalidateQueries({ queryKey: [apiPath, "one", orgId, id] });
    qc.invalidateQueries({ queryKey: ["inventory", orgId] });
    qc.invalidateQueries({ queryKey: ["item-stock", orgId] });
    qc.invalidateQueries({ queryKey: ["item-movements", orgId] });
    qc.invalidateQueries({ queryKey: ["stock-lots", orgId] });
    qc.invalidateQueries({ queryKey: ["serial-units", orgId] });
  };
}

export function useCreateDocument(apiPath: string) {
  const invalidate = useInvalidate(apiPath);
  return useMutation({
    mutationFn: async (payload: DocumentInput) =>
      (await api.post<DocumentRecord>(`/${apiPath}`, payload)).data,
    onSuccess: () => invalidate(),
  });
}

export function useUpdateDocument(apiPath: string) {
  const invalidate = useInvalidate(apiPath);
  return useMutation({
    mutationFn: async (vars: { id: number; payload: Partial<DocumentInput> }) =>
      (await api.patch<DocumentRecord>(`/${apiPath}/${vars.id}`, vars.payload)).data,
    onSuccess: (_res, vars) => invalidate(vars.id),
  });
}

export function useConvertDocument(apiPath: string) {
  const invalidate = useInvalidate(apiPath);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { id: number; target: string }) =>
      (await api.post<DocumentRecord>(`/${apiPath}/${vars.id}/convert`, { target: vars.target }))
        .data,
    onSuccess: (_res, vars) => {
      invalidate(vars.id);
      qc.invalidateQueries({ queryKey: ["invoices"] });
      qc.invalidateQueries({ queryKey: ["delivery-challans"] });
    },
  });
}

export function useFinalizeDocument(apiPath: string) {
  const invalidate = useInvalidate(apiPath);
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<DocumentRecord>(`/${apiPath}/${id}/finalize`)).data,
    onSuccess: (_res, id) => invalidate(id),
  });
}

export function useVoidDocument(apiPath: string) {
  const invalidate = useInvalidate(apiPath);
  return useMutation({
    mutationFn: async (id: number) => (await api.post<DocumentRecord>(`/${apiPath}/${id}/void`)).data,
    onSuccess: (_res, id) => invalidate(id),
  });
}

export function useDeleteDocument(apiPath: string) {
  const invalidate = useInvalidate(apiPath);
  return useMutation({
    mutationFn: (id: number) => api.delete(`/${apiPath}/${id}`),
    onSuccess: () => invalidate(),
  });
}

export function useTaxRates() {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["tax-rates", orgId],
    queryFn: async () => (await api.get<TaxRate[]>("/tax-rates")).data,
    enabled: !!token && !!orgId,
  });
}

interface TaxRateInput {
  name?: string;
  rate?: number;
  is_active?: boolean;
}

function useInvalidateTaxRates() {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return () => qc.invalidateQueries({ queryKey: ["tax-rates", orgId] });
}

export function useCreateTaxRate() {
  const invalidate = useInvalidateTaxRates();
  return useMutation({
    mutationFn: (payload: TaxRateInput) => api.post<TaxRate>("/tax-rates", payload),
    onSuccess: invalidate,
  });
}

export function useUpdateTaxRate() {
  const invalidate = useInvalidateTaxRates();
  return useMutation({
    mutationFn: (vars: { id: number; payload: TaxRateInput }) =>
      api.patch<TaxRate>(`/tax-rates/${vars.id}`, vars.payload),
    onSuccess: invalidate,
  });
}

export function useNextNumber(apiPath: string, enabled: boolean) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["next-number", orgId, apiPath],
    queryFn: async () =>
      (await api.get<{ number: string }>(`/${apiPath}/next-number`)).data,
    enabled: enabled && !!token && !!orgId,
    staleTime: 0,
  });
}

export function useStockOnHand(productIds: number[], warehouseId?: number | null) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  const ids = [...productIds].sort((a, b) => a - b);
  return useQuery({
    queryKey: ["stock-on-hand", orgId, warehouseId ?? null, ids],
    queryFn: async () => {
      const params = new URLSearchParams();
      ids.forEach((id) => params.append("product_ids", String(id)));
      if (warehouseId) params.set("warehouse_id", String(warehouseId));
      return (await api.get<Record<string, number>>(`/stock-on-hand?${params.toString()}`)).data;
    },
    enabled: !!token && !!orgId && ids.length > 0,
  });
}

export function useSellableItems(search: string, warehouseId?: number | null, limit = 50) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["sellable-items", orgId, search, warehouseId ?? null, limit],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (search) params.set("search", search);
      if (warehouseId) params.set("warehouse_id", String(warehouseId));
      return (await api.get<SellableItem[]>(`/sellable-items?${params.toString()}`)).data;
    },
    enabled: !!token && !!orgId,
  });
}
