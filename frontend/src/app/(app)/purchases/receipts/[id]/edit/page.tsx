"use client";

import { useParams } from "next/navigation";

import { errorState, loadingState, notFoundState } from "@/components/ui/QueryFallback";

import { DocumentForm } from "@/components/documents/DocumentForm";
import { useDocument } from "@/hooks/useDocuments";
import { GOODS_RECEIPT_CONFIG } from "@/lib/documentKinds";

export default function EditGoodsReceiptPage() {
  const { id } = useParams<{ id: string }>();
  const { data: doc, isLoading, error } = useDocument(GOODS_RECEIPT_CONFIG.apiPath, Number(id));

  if (error) return errorState(error);
  if (isLoading) return loadingState();
  if (!doc) return notFoundState();
  return <DocumentForm config={GOODS_RECEIPT_CONFIG} document={doc} />;
}
