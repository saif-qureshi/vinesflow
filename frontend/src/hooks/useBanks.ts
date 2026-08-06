"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type { BankAccount, BankAccountInput, BankOption } from "@/types";

export function useBankCatalog() {
  const token = useSessionStore((s) => s.accessToken);
  return useQuery({
    queryKey: ["bank-catalog"],
    queryFn: async () => (await api.get<BankOption[]>("/banks/catalog")).data,
    enabled: !!token,
    staleTime: Infinity,
  });
}

export function useBankAccounts() {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useQuery({
    queryKey: ["bank-accounts", orgId],
    queryFn: async () => (await api.get<BankAccount[]>("/banks/accounts")).data,
    enabled: !!token && !!orgId,
  });
}

function useInvalidate() {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return () => {
    qc.invalidateQueries({ queryKey: ["bank-accounts", orgId] });
    qc.invalidateQueries({ queryKey: ["accounts", orgId] });
  };
}

export function useCreateBankAccount() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (payload: BankAccountInput) => api.post<BankAccount>("/banks/accounts", payload),
    onSuccess: invalidate,
  });
}

export function useUpdateBankAccount() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (vars: { id: number; payload: BankAccountInput }) =>
      api.patch<BankAccount>(`/banks/accounts/${vars.id}`, vars.payload),
    onSuccess: invalidate,
  });
}

export function useDeleteBankAccount() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/banks/accounts/${id}`),
    onSuccess: invalidate,
  });
}
