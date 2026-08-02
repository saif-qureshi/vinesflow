"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type {
  AccessToken,
  DashboardSummary,
  Organization,
  OrganizationOnboardInput,
  OrganizationPage,
  OrganizationUpdateInput,
  SuperAdmin,
} from "@/types";

const base = "/super-admin";

export function useSuperAdmin() {
  const token = useSessionStore((state) => state.accessToken);
  return useQuery({
    queryKey: ["super-admin"],
    queryFn: async () => (await api.get<SuperAdmin>(`${base}/auth/me`)).data,
    enabled: Boolean(token),
    retry: false,
  });
}

export function useAdminLogin() {
  const setAccessToken = useSessionStore((state) => state.setAccessToken);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { email: string; password: string }) =>
      (await api.post<AccessToken>(`${base}/auth/login`, input)).data,
    onSuccess: async (data) => {
      setAccessToken(data.access_token);
      await queryClient.invalidateQueries({ queryKey: ["super-admin"] });
    },
  });
}

export function useAdminLogout() {
  const clear = useSessionStore((state) => state.clear);
  const queryClient = useQueryClient();
  return async () => {
    try {
      await api.post(`${base}/auth/logout`);
    } finally {
      clear();
      queryClient.clear();
    }
  };
}

export function useDashboard() {
  return useQuery({
    queryKey: ["super-admin-dashboard"],
    queryFn: async () => (await api.get<DashboardSummary>(`${base}/dashboard`)).data,
  });
}

export function useOrganizations(search: string, page: number) {
  return useQuery({
    queryKey: ["super-admin-organizations", search, page],
    queryFn: async () =>
      (
        await api.get<OrganizationPage>(`${base}/organizations`, {
          params: { search: search || undefined, page, page_size: 20 },
        })
      ).data,
  });
}

export function useOrganization(id: number) {
  return useQuery({
    queryKey: ["super-admin-organization", id],
    queryFn: async () => (await api.get<Organization>(`${base}/organizations/${id}`)).data,
    enabled: Number.isInteger(id) && id > 0,
  });
}

export function useOnboardOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: OrganizationOnboardInput) =>
      (await api.post<Organization>(`${base}/organizations`, input)).data,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["super-admin-organizations"] }),
        queryClient.invalidateQueries({ queryKey: ["super-admin-dashboard"] }),
      ]);
    },
  });
}

export function useSetOrganizationStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, isActive }: { id: number; isActive: boolean }) =>
      (
        await api.patch<Organization>(`${base}/organizations/${id}/status`, {
          is_active: isActive,
        })
      ).data,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["super-admin-organizations"] }),
        queryClient.invalidateQueries({ queryKey: ["super-admin-dashboard"] }),
      ]);
    },
  });
}

export function useUpdateOrganization(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: OrganizationUpdateInput) =>
      (await api.put<Organization>(`${base}/organizations/${id}`, input)).data,
    onSuccess: async (organization) => {
      queryClient.setQueryData(["super-admin-organization", id], organization);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["super-admin-organizations"] }),
        queryClient.invalidateQueries({ queryKey: ["super-admin-dashboard"] }),
      ]);
    },
  });
}
