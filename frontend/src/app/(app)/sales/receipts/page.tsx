"use client";

import { DocumentList } from "@/components/documents/DocumentList";
import { SALES_RECEIPT_CONFIG } from "@/lib/documentKinds";

export default function SalesReceiptsPage() {
  return <DocumentList config={SALES_RECEIPT_CONFIG} />;
}
