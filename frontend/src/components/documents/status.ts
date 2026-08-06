import type { DocumentKindConfig } from "@/lib/documentKinds";
import type { DocumentPaymentStatus, DocumentStatus } from "@/types";

const LIFECYCLE_META: Record<DocumentStatus, { label: string; color?: string }> = {
  draft: { label: "Draft" },
  sent: { label: "Sent", color: "blue" },
  closed: { label: "Closed", color: "default" },
  void: { label: "Void", color: "red" },
};

export const PAYMENT_META: Record<DocumentPaymentStatus, { label: string; color?: string }> = {
  unpaid: { label: "Unpaid", color: "gold" },
  partial: { label: "Partially Paid", color: "orange" },
  paid: { label: "Paid", color: "green" },
  credited: { label: "Credited", color: "purple" },
};

/** The lifecycle tag, with per-document-type wording (a confirmed sales order
 *  reads "Confirmed", a dispatched challan "Delivered"). */
export function lifecycleMeta(status: DocumentStatus, config?: DocumentKindConfig) {
  const base = LIFECYCLE_META[status] ?? { label: status, color: undefined };
  return { label: config?.statusOverrides?.[status] ?? base.label, color: base.color };
}

export function documentFilterOptions(config?: DocumentKindConfig) {
  const sentLabel = config?.statusOverrides?.sent ?? "Sent";
  if (!config?.tracksPayment) {
    return [
      { value: "draft", label: "Draft" },
      { value: "sent", label: sentLabel },
      { value: "closed", label: "Closed" },
      { value: "void", label: "Void" },
    ];
  }
  return [
    { value: "draft", label: "Draft" },
    { value: "unpaid", label: "Unpaid" },
    { value: "partial", label: "Partially Paid" },
    { value: "paid", label: "Paid" },
    { value: "void", label: "Void" },
  ];
}
