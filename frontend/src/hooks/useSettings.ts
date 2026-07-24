"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";

export function useSettingsGroup<T extends Record<string, unknown>>(group: string) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["settings", orgId, group],
    queryFn: async () => (await api.get<T>(`/settings/${group}`)).data,
    enabled: !!token && !!orgId,
  });
}

export function useUpdateSettingsGroup(group: string) {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useMutation({
    mutationFn: (values: Record<string, unknown>) => api.put(`/settings/${group}`, values),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings", orgId, group] }),
  });
}
