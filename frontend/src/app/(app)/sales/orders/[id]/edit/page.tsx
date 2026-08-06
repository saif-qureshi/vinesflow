"use client";

import { useParams } from "next/navigation";

import { errorState, loadingState, notFoundState } from "@/components/ui/QueryFallback";

import { DocumentForm } from "@/components/documents/DocumentForm";
import { useDocument } from "@/hooks/useDocuments";
import { SALES_ORDER_CONFIG } from "@/lib/documentKinds";

export default function EditSalesOrderPage() {
  const { id } = useParams<{ id: string }>();
  const { data: doc, isLoading, error } = useDocument(SALES_ORDER_CONFIG.apiPath, Number(id));

  if (error) return errorState(error);
  if (isLoading) return loadingState();
  if (!doc) return notFoundState();
  return <DocumentForm config={SALES_ORDER_CONFIG} document={doc} />;
}
