"use client";

import { useParams } from "next/navigation";

import { errorState, loadingState, notFoundState } from "@/components/ui/QueryFallback";

import { DocumentForm } from "@/components/documents/DocumentForm";
import { useDocument } from "@/hooks/useDocuments";
import { CREDIT_NOTE_CONFIG } from "@/lib/documentKinds";

export default function EditCreditNotePage() {
  const { id } = useParams<{ id: string }>();
  const { data: doc, isLoading, error } = useDocument(CREDIT_NOTE_CONFIG.apiPath, Number(id));

  if (error) return errorState(error);
  if (isLoading) return loadingState();
  if (!doc) return notFoundState();
  return <DocumentForm config={CREDIT_NOTE_CONFIG} document={doc} />;
}
