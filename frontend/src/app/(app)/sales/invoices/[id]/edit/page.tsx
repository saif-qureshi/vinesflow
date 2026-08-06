"use client";

import { useParams } from "next/navigation";

import { errorState, loadingState, notFoundState } from "@/components/ui/QueryFallback";

import { DocumentForm } from "@/components/documents/DocumentForm";
import { useDocument } from "@/hooks/useDocuments";
import { INVOICE_CONFIG } from "@/lib/documentKinds";

export default function EditInvoicePage() {
  const { id } = useParams<{ id: string }>();
  const { data: invoice, isLoading, error } = useDocument(INVOICE_CONFIG.apiPath, Number(id));

  if (error) return errorState(error);
  if (isLoading) return loadingState();
  if (!invoice) return notFoundState();
  return <DocumentForm config={INVOICE_CONFIG} document={invoice} />;
}
