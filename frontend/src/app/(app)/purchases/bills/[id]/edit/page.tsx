"use client";

import { useParams } from "next/navigation";

import { errorState, loadingState, notFoundState } from "@/components/ui/QueryFallback";

import { DocumentForm } from "@/components/documents/DocumentForm";
import { useDocument } from "@/hooks/useDocuments";
import { BILL_CONFIG } from "@/lib/documentKinds";

export default function EditBillPage() {
  const { id } = useParams<{ id: string }>();
  const { data: bill, isLoading, error } = useDocument(BILL_CONFIG.apiPath, Number(id));

  if (error) return errorState(error);
  if (isLoading) return loadingState();
  if (!bill) return notFoundState();
  return <DocumentForm config={BILL_CONFIG} document={bill} />;
}
