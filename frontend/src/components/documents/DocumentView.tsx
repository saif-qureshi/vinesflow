"use client";

import { Fragment, type ReactNode, useState } from "react";
import { useRouter } from "next/navigation";

import { errorState, loadingState, notFoundState } from "@/components/ui/QueryFallback";
import { Descriptions, Table } from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  AlertTriangle,
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

import { App, Button, Card, Dropdown, Modal, Popconfirm, Tag, Tooltip, Typography } from "@/components/ui";
import { PaymentModal } from "@/components/payments/PaymentModal";
import { useCurrency } from "@/hooks/useCurrency";
import { useBins } from "@/hooks/useBins";
import {
  useConvertDocument,
  useDeleteDocument,
  useDocument,
  useFinalizeDocument,
  useVoidDocument,
} from "@/hooks/useDocuments";
import { useValidateInvoice, type FbrError } from "@/hooks/useFbr";
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

const FBR_CREDIT_NOTE_DOC_URL =
  "https://download1.fbr.gov.pk/Docs/2017831184658713SALESTAXACT,1990Amededupto01.07.2017.pdf";

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
  const { data: doc, isLoading, error } = useDocument(config.apiPath, id);
  const { data: bins } = useBins(doc?.warehouse_id, false, doc?.warehouse_id != null);
  const finalize = useFinalizeDocument(config.apiPath);
  const voidDoc = useVoidDocument(config.apiPath);
  const del = useDeleteDocument(config.apiPath);
  const convert = useConvertDocument(config.apiPath);
  const validate = useValidateInvoice();
  const [payOpen, setPayOpen] = useState(false);
  const [printing, setPrinting] = useState(false);
  const [validation, setValidation] = useState<FbrError[] | null>(null);

  const fbrEnabled = !!currentMembership?.organization.fbr_enabled;
  const showFbrValidate =
    fbrEnabled && (config.kind === "invoice" || config.kind === "credit_note");
  const supportsBins = config.kind !== "sales_order" && config.kind !== "purchase_order";

  if (error) return errorState(error);
  if (isLoading) return loadingState();
  if (!doc) return notFoundState();

  const dash = <span className="text-gray-400">—</span>;
  const isDraft = doc.status === "draft";
  const life = lifecycleMeta(doc.status, config);
  const paidMeta = PAYMENT_META[doc.payment_status];
  const secondaryDate = config.secondaryDateField
    ? doc[config.secondaryDateField]
    : null;

  const creditNoteUnregistered =
    fbrEnabled && config.kind === "credit_note" && !doc.buyer_registered;
  const fbrUnregisteredTitle = (
    <span>
      FBR credit notes require a sales-tax-registered buyer (with STRN); this customer is
      unregistered.{" "}
      <a href={FBR_CREDIT_NOTE_DOC_URL} target="_blank" rel="noreferrer" className="underline">
        Learn more
      </a>
    </span>
  );
  const blockTip = (node: ReactNode, blocked: boolean) =>
    blocked ? (
      <Tooltip title={fbrUnregisteredTitle}>
        <span className="inline-block cursor-not-allowed">{node}</span>
      </Tooltip>
    ) : (
      node
    );

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
    ...((supportsBins && (bins?.length ?? 0) > 0) || doc.lines.some((line) => line.bin_id != null)
      ? ([
          {
            title: "Bin",
            key: "bin",
            render: (_: unknown, line: DocumentLine) => {
              if (line.bin_id == null) return "Unassigned";
              const bin = bins?.find((row) => row.id === line.bin_id);
              return bin ? `${bin.code} · ${bin.name}` : `#${line.bin_id}`;
            },
          },
        ] as ColumnsType<DocumentLine>)
      : []),
    ...(doc.lines.some(
      (line) => line.lot_allocations.length > 0 || line.serials.length > 0,
    )
      ? ([
          {
            title: "Tracking",
            key: "tracking",
            render: (_: unknown, line: DocumentLine) => {
              if (line.lot_allocations.length) {
                return (
                  <div className="space-y-0.5 text-xs">
                    {line.lot_allocations.map((allocation) => (
                      <div key={allocation.id ?? allocation.lot_id}>
                        <span className="font-medium">{allocation.lot?.lot_number ?? allocation.lot_number}</span>
                        <span className="text-gray-400"> · {Number(allocation.quantity)}</span>
                      </div>
                    ))}
                  </div>
                );
              }
              if (line.serials.length) {
                const labels = line.serials.map((serial) => serial.serial_number);
                return (
                  <Tooltip title={labels.join(", ")}>
                    <span className="cursor-help text-xs">
                      {labels.slice(0, 2).join(", ")}
                      {labels.length > 2 ? ` +${labels.length - 2}` : ""}
                    </span>
                  </Tooltip>
                );
              }
              return dash;
            },
          },
        ] as ColumnsType<DocumentLine>)
      : []),
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
              <Typography.Text type="secondary">{doc.party?.name}</Typography.Text>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {doc.status === "sent" &&
            can(`${config.permission}:update`) &&
            (config.conversions ?? []).map((conversion) => {
              const isCredit = conversion.target === "credit_note";
              if (isCredit && fbrEnabled && doc.credit_notes.length > 0) return null;
              const blocked = isCredit && fbrEnabled && !doc.buyer_registered;
              const button = (
                <Button
                  icon={<ArrowRightLeft size={16} />}
                  loading={convert.isPending}
                  disabled={blocked}
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
              );
              return <Fragment key={conversion.target}>{blockTip(button, blocked)}</Fragment>;
            })}
          {showFbrValidate &&
            !doc.fbr_invoice_number &&
            blockTip(
              <Button
                icon={<ShieldCheck size={16} />}
                loading={validate.isPending}
                disabled={creditNoteUnregistered}
                onClick={async () => {
                  try {
                    const res = await validate.mutateAsync(doc.id);
                    if (res.valid) {
                      message.success("FBR validation passed");
                    } else {
                      setValidation(res.errors);
                    }
                  } catch (err) {
                    message.error(apiErrorMessage(err));
                  }
                }}
              >
                Validate with FBR
              </Button>,
              creditNoteUnregistered,
            )}
          {isDraft && can(`${config.permission}:update`) && (
            <>
              <Button
                icon={<Pencil size={16} />}
                onClick={() => router.push(`${config.basePath}/${doc.id}/edit`)}
              >
                Edit
              </Button>
              {blockTip(
                <Button
                  type="primary"
                  icon={<CheckCircle2 size={16} />}
                  loading={finalize.isPending}
                  disabled={creditNoteUnregistered}
                  onClick={() =>
                    run(() => finalize.mutateAsync(doc.id), `${config.labels.singular} finalized`)
                  }
                >
                  Finalize
                </Button>,
                creditNoteUnregistered,
              )}
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
                  label: "Download",
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
          {config.secondaryDateField && (
            <Descriptions.Item label={config.labels.secondaryDateLabel}>
              {secondaryDate ? formatDate(secondaryDate) : dash}
            </Descriptions.Item>
          )}
          <Descriptions.Item label={config.labels.referenceLabel}>
            {doc.reference || dash}
          </Descriptions.Item>
          {config.tracksPayment && (
            <Descriptions.Item label="Amount paid">
              <span className="tabular-nums">{money(Number(doc.amount_paid))}</span>
            </Descriptions.Item>
          )}
          {doc.salesperson && (
            <Descriptions.Item label="Salesperson">
              {doc.salesperson.name}
              {Number(doc.commission_amount) > 0 && (
                <span className="ml-2 text-gray-500">
                  {money(Number(doc.commission_amount))} commission
                </span>
              )}
            </Descriptions.Item>
          )}
          {config.tracksPayment && Number(doc.amount_credited) > 0 && (
            <Descriptions.Item label="Credit notes applied">
              <span className="tabular-nums">{money(Number(doc.amount_credited))}</span>
            </Descriptions.Item>
          )}
          {config.tracksPayment && (
            <Descriptions.Item label="Balance due">
              <span className="tabular-nums font-medium">{money(Number(doc.balance_due))}</span>
            </Descriptions.Item>
          )}
          {doc.fbr_reason && (
            <Descriptions.Item label="FBR reason">
              {doc.fbr_reason}
              {doc.fbr_reason_remarks ? ` — ${doc.fbr_reason_remarks}` : ""}
            </Descriptions.Item>
          )}
          {doc.credit_notes.length > 0 && (
            <Descriptions.Item label="Credit notes">
              <span className="flex flex-wrap gap-x-3 gap-y-1">
                {doc.credit_notes.map((cn) => (
                  <Button
                    key={cn.id}
                    type="link"
                    size="small"
                    className="!h-auto !px-0"
                    onClick={() => router.push(`/sales/credit-notes/${cn.id}`)}
                  >
                    {cn.number}
                    <span className="ml-1 text-xs text-gray-400">({cn.status})</span>
                  </Button>
                ))}
              </span>
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      {doc.fbr_invoice_number && (
        <Card className="border-gray-100">
          <div className="flex items-center gap-5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/fbr-logo.png"
              alt="FBR Digital Invoicing System"
              className="h-20 w-20 shrink-0 object-contain"
            />
            {doc.fbr_qr && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={doc.fbr_qr}
                alt="FBR e-invoice QR code"
                className="h-24 w-24 shrink-0 rounded ring-1 ring-gray-100"
              />
            )}
            <div className="min-w-0">
              <div className="text-xs text-gray-400">FBR Invoice Reference Number (IRN)</div>
              <div className="font-mono text-sm break-all text-gray-800">
                {doc.fbr_invoice_number}
              </div>
              {doc.fbr_submitted_at && (
                <div className="mt-1 text-xs text-gray-400">
                  Filed {formatDate(doc.fbr_submitted_at)}
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

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
            {config.tracksPayment && Number(doc.amount_credited) > 0 && (
              <Row label="Credit notes applied" value={money(Number(doc.amount_credited))} />
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
        width={560}
      >
        {validation && <FbrValidationResult errors={validation} />}
      </Modal>
    </div>
  );
}

function FbrValidationResult({ errors }: { errors: FbrError[] }) {
  const groups: { message: string; items: string[] }[] = [];
  const seen = new Map<string, number>();
  for (const e of errors) {
    let idx = seen.get(e.msg);
    if (idx === undefined) {
      idx = groups.length;
      seen.set(e.msg, idx);
      groups.push({ message: e.msg, items: [] });
    }
    if (e.item) groups[idx].items.push(e.item);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 rounded-lg bg-rose-50 px-3 py-2 text-rose-700">
        <AlertTriangle size={18} className="shrink-0" />
        <span className="text-sm font-medium">
          FBR rejected this invoice — {groups.length} issue{groups.length === 1 ? "" : "s"} to fix
        </span>
      </div>

      <div className="max-h-[45vh] space-y-2 overflow-y-auto">
        {groups.map((g, i) => (
          <div key={i} className="rounded-lg border border-rose-100 bg-white px-3 py-2.5">
            {g.items.length > 0 && (
              <div className="mb-1.5 flex flex-wrap gap-1">
                {g.items.map((n) => (
                  <Tag key={n} color="red" className="!m-0">
                    Item {n}
                  </Tag>
                ))}
              </div>
            )}
            <div className="text-sm text-gray-700">{g.message}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
