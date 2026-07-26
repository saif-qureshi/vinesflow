"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type { Product, ProductInput } from "@/types";

interface ProductPage {
  items: Product[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface ProductFilters {
  search?: string;
  category_id?: number | null;
  nature?: "good" | "service" | null;
  type?: "single" | "variable" | null;
  is_active?: boolean | null;
}

export function useProducts(filters: ProductFilters = {}, limit = 25) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useInfiniteQuery({
    queryKey: ["products", orgId, filters],
    queryFn: async ({ pageParam }) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (pageParam) params.set("cursor", pageParam as string);
      if (filters.search) params.set("search", filters.search);
      if (filters.category_id != null) params.set("category_id", String(filters.category_id));
      if (filters.nature) params.set("nature", filters.nature);
      if (filters.type) params.set("type", filters.type);
      if (filters.is_active != null) params.set("is_active", String(filters.is_active));
      return (await api.get<ProductPage>(`/products?${params.toString()}`)).data;
    },
    initialPageParam: null as string | null,
    getNextPageParam: (last) => (last.has_more ? last.next_cursor : undefined),
    enabled: !!token && !!orgId,
  });
}

export function useProduct(id: number | null) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["product", orgId, id],
    queryFn: async () => (await api.get<Product>(`/products/${id}`)).data,
    enabled: !!token && !!orgId && !!id,
  });
}

export function useItemSales(productId: number, period: "month" | "quarter" | "year") {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["item-sales", orgId, productId, period],
    queryFn: async () =>
      (
        await api.get<{ label: string; sales: number }[]>(
          `/products/${productId}/sales?period=${period}`,
        )
      ).data,
    enabled: !!token && !!orgId && !!productId,
  });
}

function useInvalidate() {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return () => qc.invalidateQueries({ queryKey: ["products", orgId] });
}

export function useCreateProduct() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: ProductInput) => api.post<Product>("/products", payload),
    onSuccess: invalidate,
  });
}

export function useUpdateProduct() {
  const invalidate = useInvalidate();
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useMutation({
    mutationFn: (vars: { id: number; payload: Partial<ProductInput> }) =>
      api.patch<Product>(`/products/${vars.id}`, vars.payload),
    onSuccess: (_res, vars) => {
      invalidate();
      qc.invalidateQueries({ queryKey: ["product", orgId, vars.id] });
    },
  });
}

export function useDeleteProduct() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/products/${id}`),
    onSuccess: invalidate,
  });
}
