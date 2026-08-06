"use client";

import { useParams } from "next/navigation";

import { errorState, loadingState, notFoundState } from "@/components/ui/QueryFallback";

import { DocumentForm } from "@/components/documents/DocumentForm";
import { useDocument } from "@/hooks/useDocuments";
import { DELIVERY_CHALLAN_CONFIG } from "@/lib/documentKinds";

export default function EditDeliveryChallanPage() {
  const { id } = useParams<{ id: string }>();
  const { data: doc, isLoading, error } = useDocument(DELIVERY_CHALLAN_CONFIG.apiPath, Number(id));

  if (error) return errorState(error);
  if (isLoading) return loadingState();
  if (!doc) return notFoundState();
  return <DocumentForm config={DELIVERY_CHALLAN_CONFIG} document={doc} />;
}
