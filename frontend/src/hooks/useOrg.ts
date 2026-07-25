"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Address } from "@/types";

export function useUpdateOrg() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      name?: string;
      currency?: string;
      industry?: string;
      country?: string;
      ntn?: string;
      strn?: string;
      cnic?: string;
      address?: Address | null;
      fiscal_year_start_month?: number;
      logo_url?: string;
      theme?: "light" | "dark";
      accent_color?: string;
      keep_branding?: boolean;
      fbr_enabled?: boolean;
      fbr_environment?: "sandbox" | "production";
      fbr_province?: string;
      fbr_sandbox_token?: string;
      fbr_production_token?: string;
    }) => api.patch("/orgs/current", vars),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { full_name?: string; password?: string; avatar_url?: string }) =>
      api.patch("/users/me", vars),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}
