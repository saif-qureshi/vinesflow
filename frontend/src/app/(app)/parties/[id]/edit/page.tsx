"use client";

import { useParams } from "next/navigation";

import { errorState, loadingState, notFoundState } from "@/components/ui/QueryFallback";

import { PartyForm } from "@/components/parties/PartyForm";
import { useParty } from "@/hooks/useParties";

export default function EditPartyPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, error } = useParty(Number(id));

  if (error) return errorState(error);
  if (isLoading) return loadingState();
  if (!data) return notFoundState();

  return <PartyForm key={data.id} party={data} />;
}
