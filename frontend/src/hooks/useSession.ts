"use client";

import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type { AccessToken, Me } from "@/types";

export function useMe() {
  const token = useSessionStore((s) => s.accessToken);
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => (await api.get<Me>("/auth/me")).data,
    enabled: !!token,
    staleTime: 60_000,
    retry: false,
  });
}

export function useSession() {
  const { data, isLoading } = useMe();
  const currentOrgId = useSessionStore((s) => s.currentOrgId);
  const token = useSessionStore((s) => s.accessToken);
  const memberships = data?.memberships ?? [];
  return {
    user: data?.user ?? null,
    memberships,
    currentOrgId,
    currentMembership: memberships.find((m) => m.org_id === currentOrgId) ?? null,
    isAuthenticated: !!token && !!data,
    isLoading: !!token && isLoading,
  };
}

export function usePermissions() {
  const token = useSessionStore((s) => s.accessToken);
  const currentOrgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["my-permissions", currentOrgId],
    queryFn: async () => (await api.get<string[]>("/orgs/current/my-permissions")).data,
    enabled: !!token && !!currentOrgId,
    staleTime: 60_000,
  });
}

export function useCan() {
  const { data } = usePermissions();
  const set = useMemo(() => new Set(data ?? []), [data]);
  return (code: string) => set.has(code);
}

export function useLogin() {
  const setAccessToken = useSessionStore((s) => s.setAccessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { email: string; password: string }) =>
      (await api.post<AccessToken>("/auth/login", vars)).data,
    onSuccess: async (data) => {
      setAccessToken(data.access_token);
      await qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useLogout() {
  const clear = useSessionStore((s) => s.clear);
  const setCurrentOrgId = useSessionStore((s) => s.setCurrentOrgId);
  const qc = useQueryClient();
  return async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      // ignore; we clear locally regardless
    }
    clear();
    setCurrentOrgId(null);
    qc.clear();
  };
}

export function useSwitchOrg() {
  return useSessionStore((s) => s.setCurrentOrgId);
}

export function useAppTheme(): { theme: "light" | "dark"; accent: string } {
  const { currentMembership } = useSession();
  const org = currentMembership?.organization;
  return { theme: org?.theme ?? "light", accent: org?.accent_color ?? "#2563eb" };
}
