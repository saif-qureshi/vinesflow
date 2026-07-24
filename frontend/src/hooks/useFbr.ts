"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";

export interface FbrOption {
  value: string;
  label: string;
}

export interface FbrReference {
  code: string;
  description: string | null;
  value: number | null;
  parent_code: string | null;
}

export type FbrReferenceType = "hs_code" | "uom" | "sale_type" | "tax_rate" | "sro_schedule";

export function useFbrProvinces() {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["fbr", "provinces"],
    queryFn: async () => (await api.get<FbrOption[]>("/fbr/provinces")).data,
    enabled: !!token && !!orgId,
    staleTime: Infinity,
  });
}

export function useFbrHsUom(hsCode?: string) {
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["fbr", "hs-uom", hsCode ?? null],
    queryFn: async () =>
      (await api.get<FbrReference[]>("/fbr/hs-uom", { params: { hs_code: hsCode } })).data,
    enabled: !!hsCode && !!orgId,
    staleTime: 60 * 60 * 1000,
  });
}

export function useFbrSroItems(sroId?: string) {
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["fbr", "sro-items", sroId ?? null],
    queryFn: async () =>
      (await api.get<FbrReference[]>("/fbr/sro-items", { params: { sro_id: sroId } })).data,
    enabled: !!sroId && !!orgId,
    staleTime: 60 * 60 * 1000,
  });
}

export function useFbrReference(
  type: FbrReferenceType,
  opts: { parent?: string; search?: string; enabled?: boolean },
) {
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["fbr", "reference", type, opts.parent ?? null, opts.search ?? ""],
    queryFn: async () =>
      (
        await api.get<FbrReference[]>(`/fbr/reference/${type}`, {
          params: { parent: opts.parent, search: opts.search || undefined, limit: 100 },
        })
      ).data,
    enabled: (opts.enabled ?? true) && !!orgId,
    staleTime: 5 * 60 * 1000,
  });
}
