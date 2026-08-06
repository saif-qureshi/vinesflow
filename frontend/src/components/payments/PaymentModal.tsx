"use client";

import { useState } from "react";
import { DatePicker, InputNumber, Modal, Table } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";

import { App, Button, Input, Select, TextArea } from "@/components/ui";
import { useCurrency } from "@/hooks/useCurrency";
import { useCreatePayment, useOutstandingDocuments, useSubmitPayment } from "@/hooks/usePayments";
import { PartySelect } from "@/components/parties/PartySelect";
import { apiErrorMessage } from "@/lib/api";
import type { PaymentKindConfig } from "@/lib/paymentKinds";
import { formatDate } from "@/lib/format";
import type { DocumentRecord, OutstandingDocument, PaymentMethod } from "@/types";

const METHODS = [
  { value: "cash", label: "Cash" },
  { value: "bank", label: "Bank Transfer" },
  { value: "cheque", label: "Cheque" },
  { value: "card", label: "Card" },
  { value: "other", label: "Other" },
];

export function PaymentModal({
  config,
  document,
  open,
  onClose,
}: {
  config: PaymentKindConfig;
  document?: DocumentRecord;
  open: boolean;
  onClose: () => void;
}) {
  const { message } = App.useApp();
  const { currency, money } = useCurrency();
  const create = useCreatePayment(config.apiPath);
  const submit = useSubmitPayment(config.apiPath);

  const [partyId, setPartyId] = useState<number | undefined>(document?.party_id ?? undefined);
  const [date, setDate] = useState(dayjs());
  const [method, setMethod] = useState<PaymentMethod>("cash");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");
  const [amount, setAmount] = useState<number>(document ? Number(document.balance_due) : 0);
  const [applied, setApplied] = useState<Record<number, number>>(
    document ? { [document.id]: Number(document.balance_due) } : {},
  );

  const { data: outstanding } = useOutstandingDocuments(config.direction, partyId ?? null);
  const rows = outstanding ?? [];

  const allocated = Object.values(applied).reduce((sum, v) => sum + (v || 0), 0);
  const unapplied = amount - allocated;
  const saving = create.isPending || submit.isPending;

  const onSelectParty = (v: number) => {
    setPartyId(v);
    setApplied({});
  };

  const setApply = (docId: number, value: number) =>
    setApplied((prev) => ({ ...prev, [docId]: value }));

  const distribute = (amt: number): Record<number, number> => {
    const ordered = [...rows];
    if (document) {
      ordered.sort(
        (a, b) => Number(b.id === document.id) - Number(a.id === document.id),
      );
    }
    let remaining = amt;
    const next: Record<number, number> = {};
    for (const doc of ordered) {
      const apply = Math.min(Number(doc.balance_due), Math.max(remaining, 0));
      if (apply > 0) next[doc.id] = apply;
      remaining -= apply;
    }
    return next;
  };

  const autoApply = () => setApplied(distribute(amount));

  const onAmountChange = (v: number) => {
    setAmount(v);
    if (rows.length) setApplied(distribute(v));
  };

  const columns: ColumnsType<OutstandingDocument> = [
    { title: "Document", key: "number", render: (_, d) => d.number },
    { title: "Due", key: "due", render: (_, d) => (d.due_date ? formatDate(d.due_date) : "—") },
    {
      title: "Balance",
      key: "balance",
      align: "right",
      render: (_, d) => <span className="tabular-nums">{money(Number(d.balance_due))}</span>,
    },
    {
      title: "Apply",
      key: "apply",
      width: 150,
      render: (_, d) => (
        <InputNumber
          className="!w-full"
          min={0}
          max={Number(d.balance_due)}
          prefix={currency}
          value={applied[d.id] ?? 0}
          onChange={(v) => setApply(d.id, v ?? 0)}
        />
      ),
    },
  ];

  const record = async (alsoSubmit: boolean) => {
    if (!partyId) {
      message.error(`Select a ${config.labels.party.toLowerCase()}`);
      return;
    }
    if (amount <= 0) {
      message.error("Enter a payment amount");
      return;
    }
    if (allocated > amount + 0.001) {
      message.error("Applied amount exceeds the payment amount");
      return;
    }
    const allocations = Object.entries(applied)
      .filter(([, v]) => v > 0)
      .map(([docId, v]) => ({ document_id: Number(docId), amount: v }));
    try {
      const saved = await create.mutateAsync({
        party_id: partyId,
        document_date: date.format("YYYY-MM-DD"),
        method,
        amount,
        reference: reference || null,
        notes: notes || null,
        allocations,
      });
      if (alsoSubmit) await submit.mutateAsync(saved.id);
      message.success(alsoSubmit ? "Payment recorded" : "Draft saved");
      onClose();
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={config.labels.listTitle.replace(/s$/, "")}
      width={720}
      footer={[
        <Button key="cancel" onClick={onClose}>
          Cancel
        </Button>,
        <Button key="draft" onClick={() => record(false)} loading={saving}>
          Save Draft
        </Button>,
        <Button key="record" type="primary" onClick={() => record(true)} loading={saving}>
          Record Payment
        </Button>,
      ]}
    >
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <div className="mb-1 text-sm font-medium">{config.labels.party}</div>
          <PartySelect
            role={config.partyRole}
            value={partyId}
            onChange={onSelectParty}
            placeholder={`Select ${config.labels.party.toLowerCase()}`}
            selected={document?.party ? { id: document.party.id, name: document.party.name } : null}
            disabled={!!document}
          />
        </div>
        <div>
          <div className="mb-1 text-sm font-medium">Payment date</div>
          <DatePicker value={date} onChange={(d) => d && setDate(d)} format="DD MMM YYYY" className="!w-full" />
        </div>
        <div>
          <div className="mb-1 text-sm font-medium">Amount</div>
          <InputNumber className="!w-full" min={0} prefix={currency} value={amount} onChange={(v) => onAmountChange(v ?? 0)} />
        </div>
        <div>
          <div className="mb-1 text-sm font-medium">Method</div>
          <Select value={method} onChange={setMethod} options={METHODS} className="w-full" />
        </div>
        <div>
          <div className="mb-1 text-sm font-medium">Reference</div>
          <Input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Txn / cheque no." />
        </div>
        <div>
          <div className="mb-1 text-sm font-medium">Notes</div>
          <TextArea rows={1} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>

      {partyId && (
        <div className="mt-5">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium">Apply to outstanding {config.direction === "received" ? "invoices" : "bills"}</span>
            {rows.length > 0 && (
              <Button type="link" size="small" className="!px-0" onClick={autoApply}>
                Auto-apply
              </Button>
            )}
          </div>
          <Table<OutstandingDocument>
            size="small"
            rowKey="id"
            columns={columns}
            dataSource={rows}
            pagination={false}
            locale={{ emptyText: "Nothing outstanding" }}
          />
          <div className="mt-3 flex justify-end gap-6 text-sm">
            <span className="text-gray-500">
              Applied <span className="tabular-nums font-medium text-gray-900">{money(allocated)}</span>
            </span>
            <span className="text-gray-500">
              Unapplied{" "}
              <span className={`tabular-nums font-medium ${unapplied < 0 ? "text-red-500" : "text-gray-900"}`}>
                {money(unapplied)}
              </span>
            </span>
          </div>
        </div>
      )}
    </Modal>
  );
}
