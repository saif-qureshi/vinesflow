"use client";

import { DocumentForm } from "@/components/documents/DocumentForm";
import { SALES_RECEIPT_CONFIG } from "@/lib/documentKinds";

export default function NewSalesReceiptPage() {
  return <DocumentForm config={SALES_RECEIPT_CONFIG} />;
}
