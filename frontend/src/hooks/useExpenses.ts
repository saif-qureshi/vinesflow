"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type { ExpenseInput, ExpenseRecord, ExpenseStatus, ExpenseSummary } from "@/types";

interface ExpensePage {
  items: ExpenseSummary[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface ExpenseFilters {
  search?: string;
  status?: ExpenseStatus | null;
  vendor_id?: number | null;
}

export function useExpenseList(filters: ExpenseFilters = {}, limit = 25) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useInfiniteQuery({
    queryKey: ["expenses", orgId, filters],
    queryFn: async ({ pageParam }) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (pageParam) params.set("cursor", pageParam as string);
      if (filters.search) params.set("search", filters.search);
      if (filters.status) params.set("status", filters.status);
      if (filters.vendor_id != null) params.set("vendor_id", String(filters.vendor_id));
      return (await api.get<ExpensePage>(`/expenses?${params.toString()}`)).data;
    },
    initialPageParam: null as string | null,
    getNextPageParam: (last) => (last.has_more ? last.next_cursor : undefined),
    enabled: !!token && !!orgId,
  });
}

export function useExpense(id: number | null) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["expenses", "one", orgId, id],
    queryFn: async () => (await api.get<ExpenseRecord>(`/expenses/${id}`)).data,
    enabled: !!token && !!orgId && !!id,
  });
}

function useInvalidate() {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return (id?: number) => {
    qc.invalidateQueries({ queryKey: ["expenses", orgId] });
    if (id) qc.invalidateQueries({ queryKey: ["expenses", "one", orgId, id] });
  };
}

export function useCreateExpense() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (payload: ExpenseInput) =>
      (await api.post<ExpenseRecord>("/expenses", payload)).data,
    onSuccess: () => invalidate(),
  });
}

export function useUpdateExpense(id: number) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (payload: ExpenseInput) =>
      (await api.patch<ExpenseRecord>(`/expenses/${id}`, payload)).data,
    onSuccess: () => invalidate(id),
  });
}

export function useSubmitExpense() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (id: number) => (await api.post<ExpenseRecord>(`/expenses/${id}/submit`)).data,
    onSuccess: (_res, id) => invalidate(id),
  });
}

export function useCancelExpense() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (id: number) => (await api.post<ExpenseRecord>(`/expenses/${id}/cancel`)).data,
    onSuccess: (_res, id) => invalidate(id),
  });
}

export function useDeleteExpense() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/expenses/${id}`),
    onSuccess: () => invalidate(),
  });
}
