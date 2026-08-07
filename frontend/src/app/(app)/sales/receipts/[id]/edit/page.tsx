"use client";

import { useParams } from "next/navigation";

import { errorState, loadingState, notFoundState } from "@/components/ui/QueryFallback";

import { DocumentForm } from "@/components/documents/DocumentForm";
import { useDocument } from "@/hooks/useDocuments";
import { SALES_RECEIPT_CONFIG } from "@/lib/documentKinds";

export default function EditSalesReceiptPage() {
  const { id } = useParams<{ id: string }>();
  const { data: receipt, isLoading, error } = useDocument(
    SALES_RECEIPT_CONFIG.apiPath,
    Number(id),
  );

  if (error) return errorState(error);
  if (isLoading) return loadingState();
  if (!receipt) return notFoundState();
  return <DocumentForm config={SALES_RECEIPT_CONFIG} document={receipt} />;
}
