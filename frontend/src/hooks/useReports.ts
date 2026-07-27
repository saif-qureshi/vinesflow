"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type { ReportListItem, ReportMeta, ReportResult } from "@/types/report";

export type ReportParams = Record<string, string | number | undefined>;

function toQuery(params: ReportParams): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  return search.toString();
}

export function useReportList() {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["reports", "list", orgId],
    queryFn: async () => (await api.get<ReportListItem[]>("/reports")).data,
    enabled: !!token && !!orgId,
  });
}

export function useReportMeta(key: string) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["reports", "meta", orgId, key],
    queryFn: async () => (await api.get<ReportMeta>(`/reports/${key}`)).data,
    enabled: !!token && !!orgId && !!key,
  });
}

export function useRunReport(key: string, params: ReportParams, enabled = true) {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["reports", "run", orgId, key, params],
    queryFn: async () =>
      (await api.get<ReportResult>(`/reports/${key}/run?${toQuery(params)}`)).data,
    enabled: !!token && !!orgId && !!key && enabled,
  });
}

export async function downloadReport(key: string, format: "pdf" | "xlsx", params: ReportParams) {
  const res = await api.get(`/reports/${key}/export?format=${format}&${toQuery(params)}`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data as Blob);
  const link = window.document.createElement("a");
  link.href = url;
  link.download = `${key}.${format}`;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 60000);
}
