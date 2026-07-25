"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Descriptions, Spin, Table } from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  ArrowLeft,
  ArrowRightLeft,
  Ban,
  CheckCircle2,
  Download,
  MoreHorizontal,
  Pencil,
  ShieldCheck,
  Trash2,
  Wallet,
} from "lucide-react";

import { App, Button, Card, Dropdown, Modal, Popconfirm, Tag, Typography } from "@/components/ui";
import { PaymentModal } from "@/components/payments/PaymentModal";
import { useCurrency } from "@/hooks/useCurrency";
import {
  useConvertDocument,
  useDeleteDocument,
  useDocument,
  useFinalizeDocument,
  useVoidDocument,
} from "@/hooks/useDocuments";
import { useValidateInvoice, type FbrValidationResponse } from "@/hooks/useFbr";
import { useCan, useSession } from "@/hooks/useSession";
import { apiErrorMessage } from "@/lib/api";
import { downloadDocumentPdf } from "@/lib/documentPdf";
import type { DocumentKindConfig } from "@/lib/documentKinds";
import { PAYMENT_CONFIG } from "@/lib/paymentKinds";
import { formatDate } from "@/lib/format";
import type { DocumentLine } from "@/types";
import { lifecycleMeta, PAYMENT_META } from "./status";

const CONVERT_TARGET_PATH: Record<string, string> = {
  delivery_challan: "/sales/challans",
  invoice: "/sales/invoices",
  credit_note: "/sales/credit-notes",
  goods_receipt: "/purchases/receipts",
  bill: "/purchases/bills",
};

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div
      className={`flex justify-between ${strong ? "border-t border-gray-100 pt-2 text-base font-semibold" : "text-sm"}`}
    >
      <span className={strong ? "" : "text-gray-500"}>{label}</span>
      <span className="tabular-nums">{value}</span>
    </div>
  );
}

export function DocumentView({ config, id }: { config: DocumentKindConfig; id: number }) {
  const router = useRouter();
  const { message } = App.useApp();
  const { money } = useCurrency();
  const can = useCan();
  const { currentMembership } = useSession();
  const { data: doc, isLoading } = useDocument(config.apiPath, id);
  const finalize = useFinalizeDocument(config.apiPath);
  const voidDoc = useVoidDocument(config.apiPath);
  const del = useDeleteDocument(config.apiPath);
  const convert = useConvertDocument(config.apiPath);
  const validate = useValidateInvoice();
  const [payOpen, setPayOpen] = useState(false);
  const [printing, setPrinting] = useState(false);
  const [validation, setValidation] = useState<FbrValidationResponse | null>(null);

  const showFbrValidate = !!currentMembership?.organization.fbr_enabled && config.kind === "invoice";

  if (isLoading || !doc) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  const dash = <span className="text-gray-400">—</span>;
  const isDraft = doc.status === "draft";
  const life = lifecycleMeta(doc.status, config);
  const paidMeta = PAYMENT_META[doc.payment_status];

  const downloadPdf = async () => {
    setPrinting(true);
    try {
      await downloadDocumentPdf(config.apiPath, doc.id, doc.number);
    } catch (err) {
      message.error(apiErrorMessage(err));
    } finally {
      setPrinting(false);
    }
  };

  const run = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      message.success(ok);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const columns: ColumnsType<DocumentLine> = [
    { title: "Description", key: "description", render: (_, l) => l.description },
    {
      title: "Qty",
      key: "qty",
      align: "right",
      render: (_, l) => <span className="tabular-nums">{Number(l.quantity)}</span>,
    },
    {
      title: "Rate",
      key: "rate",
      align: "right",
      render: (_, l) => <span className="tabular-nums">{money(Number(l.unit_price))}</span>,
    },
    {
      title: "Discount",
      key: "discount",
      align: "right",
      render: (_, l) =>
        Number(l.discount) ? <span className="tabular-nums">{money(Number(l.discount))}</span> : dash,
    },
    {
      title: "Tax",
      key: "tax",
      align: "right",
      render: (_, l) => <span className="tabular-nums">{money(Number(l.tax_amount))}</span>,
    },
    {
      title: "Amount",
      key: "amount",
      align: "right",
      render: (_, l) => (
        <span className="tabular-nums font-medium">{money(Number(l.line_total))}</span>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-6 pb-10">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-2">
          <Button
            type="text"
            icon={<ArrowLeft size={18} />}
            onClick={() => router.push(config.basePath)}
            className="!mt-0.5"
          />
          <div>
            <Typography.Title level={3} className="!mb-1">
              {doc.number}
            </Typography.Title>
            <div className="flex flex-wrap items-center gap-2">
              <Tag color={life.color}>{life.label}</Tag>
              {config.tracksPayment && doc.status === "sent" && (
                <Tag color={paidMeta.color}>{paidMeta.label}</Tag>
              )}
              {doc.fbr_invoice_number && (
                <Tag color="cyan" icon={<ShieldCheck size={12} />}>
                  FBR IRN: {doc.fbr_invoice_number}
                </Tag>
              )}
              <Typography.Text type="secondary">{doc.party?.name}</Typography.Text>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {doc.status === "sent" &&
            can(`${config.permission}:update`) &&
            (config.conversions ?? []).map((conversion) => (
              <Button
                key={conversion.target}
                icon={<ArrowRightLeft size={16} />}
                loading={convert.isPending}
                onClick={async () => {
                  try {
                    const created = await convert.mutateAsync({
                      id: doc.id,
                      target: conversion.target,
                    });
                    message.success(`Created ${created.number}`);
                    router.push(`${CONVERT_TARGET_PATH[conversion.target]}/${created.id}`);
                  } catch (err) {
                    message.error(apiErrorMessage(err));
                  }
                }}
              >
                {conversion.label}
              </Button>
            ))}
          {showFbrValidate && !doc.fbr_invoice_number && (
            <Button
              icon={<ShieldCheck size={16} />}
              loading={validate.isPending}
              onClick={async () => {
                try {
                  const res = await validate.mutateAsync(doc.id);
                  const vr = res.response?.validationResponse ?? {};
                  setValidation(vr);
                  if (vr.status === "Valid" || vr.statusCode === "00") {
                    message.success("FBR validation passed");
                  }
                } catch (err) {
                  message.error(apiErrorMessage(err));
                }
              }}
            >
              Validate with FBR
            </Button>
          )}
          {isDraft && can(`${config.permission}:update`) && (
            <>
              <Button
                icon={<Pencil size={16} />}
                onClick={() => router.push(`${config.basePath}/${doc.id}/edit`)}
              >
                Edit
              </Button>
              <Button
                type="primary"
                icon={<CheckCircle2 size={16} />}
                loading={finalize.isPending}
                onClick={() =>
                  run(() => finalize.mutateAsync(doc.id), `${config.labels.singular} finalized`)
                }
              >
                Finalize
              </Button>
            </>
          )}
          {config.tracksPayment &&
            doc.status === "sent" &&
            doc.payment_status !== "paid" &&
            Number(doc.balance_due) > 0 &&
            can("payments:create") && (
              <Button type="primary" icon={<Wallet size={16} />} onClick={() => setPayOpen(true)}>
                Record Payment
              </Button>
            )}
          {!isDraft && doc.status !== "void" && can(`${config.permission}:update`) && (
            <Popconfirm
              title={`Void this ${config.labels.singular.toLowerCase()}?`}
              description="Stock movements will be reversed."
              okText="Void"
              okButtonProps={{ danger: true, loading: voidDoc.isPending }}
              onConfirm={() =>
                run(() => voidDoc.mutateAsync(doc.id), `${config.labels.singular} voided`)
              }
            >
              <Button danger icon={<Ban size={16} />}>
                Void
              </Button>
            </Popconfirm>
          )}
          {isDraft && can(`${config.permission}:delete`) && (
            <Popconfirm
              title="Delete this draft?"
              okText="Delete"
              okButtonProps={{ danger: true, loading: del.isPending }}
              onConfirm={async () => {
                await run(() => del.mutateAsync(doc.id), `${config.labels.singular} deleted`);
                router.push(config.basePath);
              }}
            >
              <Button danger icon={<Trash2 size={16} />} />
            </Popconfirm>
          )}
          <Dropdown
            trigger={["click"]}
            placement="bottomRight"
            menu={{
              items: [
                {
                  key: "download",
                  icon: <Download size={14} />,
                  label: `Download ${config.labels.singular}`,
                  onClick: downloadPdf,
                },
              ],
            }}
          >
            <Button icon={<MoreHorizontal size={16} />} loading={printing} />
          </Dropdown>
        </div>
      </div>

      <Card className="border-gray-100">
        <Descriptions column={{ xs: 1, md: 4 }} colon={false} size="small">
          <Descriptions.Item label={config.labels.party}>
            {doc.party?.name ?? dash}
          </Descriptions.Item>
          <Descriptions.Item label={config.labels.dateLabel}>
            {formatDate(doc.issue_date)}
          </Descriptions.Item>
          <Descriptions.Item label="Due date">
            {doc.due_date ? formatDate(doc.due_date) : dash}
          </Descriptions.Item>
          <Descriptions.Item label={config.labels.referenceLabel}>
            {doc.reference || dash}
          </Descriptions.Item>
          {config.tracksPayment && (
            <Descriptions.Item label="Amount paid">
              <span className="tabular-nums">{money(Number(doc.amount_paid))}</span>
            </Descriptions.Item>
          )}
          {config.tracksPayment && (
            <Descriptions.Item label="Balance due">
              <span className="tabular-nums font-medium">{money(Number(doc.balance_due))}</span>
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card title="Items" className="border-gray-100">
        <Table<DocumentLine>
          size="small"
          rowKey="id"
          columns={columns}
          dataSource={doc.lines}
          pagination={false}
        />
        <div className="mt-6 flex justify-end">
          <div className="w-full max-w-sm space-y-2">
            <Row label="Subtotal" value={money(Number(doc.subtotal))} />
            {Number(doc.discount_total) > 0 && (
              <Row label="Discount" value={`-${money(Number(doc.discount_total))}`} />
            )}
            <Row label="Tax" value={money(Number(doc.tax_total))} />
            {Number(doc.shipping) > 0 && <Row label="Shipping" value={money(Number(doc.shipping))} />}
            {Number(doc.adjustment) !== 0 && (
              <Row label="Adjustment" value={money(Number(doc.adjustment))} />
            )}
            <Row label="Total" value={money(Number(doc.total))} strong />
            {config.tracksPayment && (
              <Row label="Amount paid" value={money(Number(doc.amount_paid))} />
            )}
            {config.tracksPayment && (
              <Row label="Balance due" value={money(Number(doc.balance_due))} strong />
            )}
          </div>
        </div>
      </Card>

      {(doc.notes || doc.terms) && (
        <Card className="border-gray-100">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {doc.notes && (
              <div>
                <div className="text-xs text-gray-400">Notes</div>
                <div className="mt-1 whitespace-pre-wrap text-sm text-gray-600">{doc.notes}</div>
              </div>
            )}
            {doc.terms && (
              <div>
                <div className="text-xs text-gray-400">Terms & conditions</div>
                <div className="mt-1 whitespace-pre-wrap text-sm text-gray-600">{doc.terms}</div>
              </div>
            )}
          </div>
        </Card>
      )}

      <PaymentModal
        config={PAYMENT_CONFIG[config.paymentDirection]}
        document={doc}
        open={payOpen}
        onClose={() => setPayOpen(false)}
      />

      <Modal
        open={validation !== null}
        onCancel={() => setValidation(null)}
        onOk={() => setValidation(null)}
        title="FBR validation"
        footer={null}
      >
        {validation && (
          <div className="space-y-3">
            <Tag color={validation.status === "Valid" || validation.statusCode === "00" ? "green" : "red"}>
              {validation.status ?? validation.statusCode ?? "Result"}
            </Tag>
            {validation.error && <div className="text-sm text-rose-600">{validation.error}</div>}
            {(validation.invoiceStatuses ?? [])
              .filter((s) => s.error)
              .map((s, i) => (
                <div key={i} className="text-sm">
                  <span className="text-gray-500">Item {s.itemSNo}: </span>
                  <span className="text-rose-600">{s.error}</span>
                </div>
              ))}
          </div>
        )}
      </Modal>
    </div>
  );
}
