"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type { NamedRecord, NamedRecordInput } from "@/types";

/** Hooks for the simple name + description + active master-data resources
 *  (brands, manufacturers). The resource is fixed per page, so these obey the
 *  rules of hooks the same way a hard-coded path would. */

export function useNamedList(resource: string, activeOnly = false) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: [resource, orgId],
    queryFn: async () => (await api.get<NamedRecord[]>(`/${resource}`)).data,
    enabled: !!token && !!orgId,
    select: activeOnly ? (rows) => rows.filter((row) => row.is_active) : undefined,
  });
}

function useInvalidate(resource: string) {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return () => qc.invalidateQueries({ queryKey: [resource, orgId] });
}

export function useCreateNamed(resource: string) {
  const invalidate = useInvalidate(resource);
  return useMutation({
    mutationFn: (payload: NamedRecordInput) => api.post<NamedRecord>(`/${resource}`, payload),
    onSuccess: invalidate,
  });
}

export function useUpdateNamed(resource: string) {
  const invalidate = useInvalidate(resource);
  return useMutation({
    mutationFn: (vars: { id: number; payload: NamedRecordInput }) =>
      api.patch<NamedRecord>(`/${resource}/${vars.id}`, vars.payload),
    onSuccess: invalidate,
  });
}

export function useDeleteNamed(resource: string) {
  const invalidate = useInvalidate(resource);
  return useMutation({
    mutationFn: (id: number) => api.delete(`/${resource}/${id}`),
    onSuccess: invalidate,
  });
}
