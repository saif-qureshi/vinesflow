"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type { DashboardSummary } from "@/types/dashboard";

export function useDashboard() {
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["dashboard", orgId],
    queryFn: async () => (await api.get<DashboardSummary>("/dashboard/summary")).data,
  });
}
