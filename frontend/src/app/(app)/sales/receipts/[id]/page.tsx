"use client";

import { useParams } from "next/navigation";

import { DocumentView } from "@/components/documents/DocumentView";
import { SALES_RECEIPT_CONFIG } from "@/lib/documentKinds";

export default function ViewSalesReceiptPage() {
  const { id } = useParams<{ id: string }>();
  return <DocumentView config={SALES_RECEIPT_CONFIG} id={Number(id)} />;
}
