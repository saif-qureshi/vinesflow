"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useSessionStore } from "@/stores/session";
import type {
  Account,
  AccountInput,
  AccountUpdateInput,
  AccountingPeriod,
  FiscalYear,
  JournalVoucherCreate,
  PeriodStatus,
  Voucher,
  VoucherSummary,
} from "@/types";

function useOrgToken() {
  const token = useSessionStore((s) => s.accessToken);
  const orgId = useSessionStore((s) => s.currentOrgId);
  return { token, orgId, enabled: !!token && !!orgId };
}

export function useAccounts() {
  const { orgId, enabled } = useOrgToken();
  return useQuery({
    queryKey: ["accounts", orgId],
    queryFn: async () => (await api.get<Account[]>("/accounting/accounts")).data,
    enabled,
  });
}

export function useCreateAccount() {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useMutation({
    mutationFn: (payload: AccountInput) => api.post<Account>("/accounting/accounts", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts", orgId] }),
  });
}

export function useUpdateAccount() {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useMutation({
    mutationFn: (vars: { id: number; payload: AccountUpdateInput }) =>
      api.patch<Account>(`/accounting/accounts/${vars.id}`, vars.payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts", orgId] }),
  });
}

export function useFiscalYears() {
  const { orgId, enabled } = useOrgToken();
  return useQuery({
    queryKey: ["fiscal-years", orgId],
    queryFn: async () => (await api.get<FiscalYear[]>("/accounting/fiscal-years")).data,
    enabled,
  });
}

export function useCreateFiscalYear() {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useMutation({
    mutationFn: () => api.post<FiscalYear>("/accounting/fiscal-years"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fiscal-years", orgId] });
      qc.invalidateQueries({ queryKey: ["periods", orgId] });
    },
  });
}

export function useDeleteFiscalYear() {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useMutation({
    mutationFn: (id: number) => api.delete(`/accounting/fiscal-years/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fiscal-years", orgId] });
      qc.invalidateQueries({ queryKey: ["periods", orgId] });
    },
  });
}

export function usePeriods(fiscalYearId?: number) {
  const { orgId, enabled } = useOrgToken();
  return useQuery({
    queryKey: ["periods", orgId, fiscalYearId ?? null],
    queryFn: async () =>
      (
        await api.get<AccountingPeriod[]>("/accounting/periods", {
          params: fiscalYearId ? { fiscal_year_id: fiscalYearId } : undefined,
        })
      ).data,
    enabled,
  });
}

export function useVouchers() {
  const { orgId, enabled } = useOrgToken();
  return useQuery({
    queryKey: ["vouchers", orgId],
    queryFn: async () => (await api.get<VoucherSummary[]>("/accounting/vouchers")).data,
    enabled,
  });
}

export function useVoucher(id: number | null) {
  const { orgId, enabled } = useOrgToken();
  return useQuery({
    queryKey: ["voucher", orgId, id],
    queryFn: async () => (await api.get<Voucher>(`/accounting/vouchers/${id}`)).data,
    enabled: enabled && !!id,
  });
}

export function useCreateVoucher() {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useMutation({
    mutationFn: (payload: JournalVoucherCreate) => api.post<Voucher>("/accounting/vouchers", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vouchers", orgId] }),
  });
}

function useVoucherAction<TArg, TData>(fn: (arg: TArg) => Promise<TData>) {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vouchers", orgId] });
      qc.invalidateQueries({ queryKey: ["voucher", orgId] });
    },
  });
}

export function useUpdateVoucher() {
  return useVoucherAction((vars: { id: number; payload: JournalVoucherCreate }) =>
    api.patch<Voucher>(`/accounting/vouchers/${vars.id}`, vars.payload),
  );
}

export function usePostVoucher() {
  return useVoucherAction((id: number) => api.post<Voucher>(`/accounting/vouchers/${id}/post`));
}

export function useCancelVoucher() {
  return useVoucherAction((id: number) => api.post<Voucher>(`/accounting/vouchers/${id}/cancel`));
}

export function useReverseVoucher() {
  return useVoucherAction((id: number) => api.post<Voucher>(`/accounting/vouchers/${id}/reverse`));
}

export function useCreateOpeningBalances() {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useMutation({
    mutationFn: (payload: {
      date: string;
      entries: { account_id: number; debit: number; credit: number }[];
    }) => api.post<Voucher>("/accounting/opening-balances", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vouchers", orgId] }),
  });
}

export function useSetPeriodStatus() {
  const qc = useQueryClient();
  const orgId = useSessionStore((s) => s.currentOrgId);
  return useMutation({
    mutationFn: (vars: { id: number; status: PeriodStatus }) =>
      api.patch<AccountingPeriod>(`/accounting/periods/${vars.id}/status`, { status: vars.status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["periods", orgId] }),
  });
}
