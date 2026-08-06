"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type { CommissionBalance, CommissionPayout, CommissionPayoutInput } from "@/types";

interface PayoutPage {
  items: CommissionPayout[];
  next_cursor: string | null;
  has_more: boolean;
}

export function useCommissionBalances() {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["commission-balances", orgId],
    queryFn: async () => (await api.get<CommissionBalance[]>("/commissions/balances")).data,
    enabled: !!token && !!orgId,
  });
}

export function useCommissionPayouts() {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["commission-payouts", orgId],
    queryFn: async () =>
      (await api.get<PayoutPage>("/commissions/payouts?limit=100")).data.items,
    enabled: !!token && !!orgId,
  });
}

function useInvalidate() {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return () => {
    qc.invalidateQueries({ queryKey: ["commission-payouts", orgId] });
    qc.invalidateQueries({ queryKey: ["commission-balances", orgId] });
  };
}

export function useCreatePayout() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: CommissionPayoutInput) =>
      api.post<CommissionPayout>("/commissions/payouts", payload),
    onSuccess: invalidate,
  });
}

export function useSubmitPayout() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: number) => api.post<CommissionPayout>(`/commissions/payouts/${id}/submit`),
    onSuccess: invalidate,
  });
}

export function useCancelPayout() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: number) => api.post<CommissionPayout>(`/commissions/payouts/${id}/cancel`),
    onSuccess: invalidate,
  });
}

export function useDeletePayout() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/commissions/payouts/${id}`),
    onSuccess: invalidate,
  });
}
