"use client";

import { useRouter } from "next/navigation";

import { errorState, loadingState, notFoundState } from "@/components/ui/QueryFallback";
import { Descriptions} from "antd";
import { BookOpen, Pencil, Trash2, X } from "lucide-react";

import { App, Avatar, Button, Card, Popconfirm, Tag, Typography } from "@/components/ui";
import { useCan } from "@/hooks/useSession";
import { useCurrency } from "@/hooks/useCurrency";
import { useDeleteParty, useParty } from "@/hooks/useParties";
import { apiErrorMessage } from "@/lib/api";
import type { Address } from "@/types";
import { PAYMENT_TERMS } from "./constants";

const dash = <span className="text-gray-400">—</span>;

function AddressBlock({ address }: { address: Address | null }) {
  if (!address || !Object.values(address).some((v) => v)) {
    return <div className="text-sm text-gray-400">No address</div>;
  }
  const lines = [
    address.attention,
    address.line1,
    address.line2,
    [address.city, address.state, address.postal_code].filter(Boolean).join(", "),
    address.country,
    address.phone,
  ].filter(Boolean);
  return (
    <div className="text-sm text-gray-600">
      {lines.map((l, i) => (
        <div key={i}>{l}</div>
      ))}
    </div>
  );
}

function BalanceCard({ balance }: { balance: number }) {
  const { money } = useCurrency();
  const settled = balance === 0;
  const owesUs = balance > 0;
  const label = settled ? "Nothing outstanding" : owesUs ? "Owes you" : "You owe";
  const tone = settled ? "text-slate-800" : owesUs ? "text-emerald-700" : "text-red-600";
  return (
    <Card className="border-gray-100">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${tone}`}>
        {money(Math.abs(balance))}
      </p>
    </Card>
  );
}

function termLabel(days: number | null) {
  if (days == null) return dash;
  return PAYMENT_TERMS.find((t) => t.value === days)?.label ?? `Net ${days}`;
}

export function PartyView({ id }: { id: number }) {
  const router = useRouter();
  const { message } = App.useApp();
  const can = useCan();
  const del = useDeleteParty();
  const { data: p, isLoading, error } = useParty(id);

  if (error) return errorState(error);
  if (isLoading) return loadingState();
  if (!p) return notFoundState();

  const remove = async () => {
    try {
      await del.mutateAsync(p.id);
      message.success("Party deleted");
      router.push("/parties");
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const contactName = [p.salutation, p.first_name, p.last_name].filter(Boolean).join(" ");

  return (
    <div className="space-y-8 pb-10">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Avatar
            shape="square"
            size={48}
            src={p.avatar_url ?? undefined}
            className="shrink-0 !bg-gray-100 !text-gray-500"
          >
            {p.name.charAt(0).toUpperCase()}
          </Avatar>
          <div>
            <Typography.Title level={3} className="!mb-1">
              {p.name}
            </Typography.Title>
            <div className="flex flex-wrap gap-1">
              {p.is_customer && <Tag color="blue">Customer</Tag>}
              {p.is_vendor && <Tag color="purple">Vendor</Tag>}
              <Tag className="capitalize">{p.type}</Tag>
              {p.is_active ? <Tag color="green">Active</Tag> : <Tag>Inactive</Tag>}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {can("reports:read") && (
            <Button
              icon={<BookOpen size={16} />}
              onClick={() => router.push(`/reports/party_ledger?party_id=${p.id}`)}
            >
              Open Ledger
            </Button>
          )}
          {can("parties:update") && (
            <Button icon={<Pencil size={16} />} onClick={() => router.push(`/parties/${p.id}/edit`)}>
              Edit
            </Button>
          )}
          {can("parties:delete") && (
            <Popconfirm
              title="Delete this party?"
              description="This cannot be undone."
              okText="Delete"
              okButtonProps={{ danger: true, loading: del.isPending }}
              onConfirm={remove}
            >
              <Button danger icon={<Trash2 size={16} />}>
                Delete
              </Button>
            </Popconfirm>
          )}
          <Button type="text" icon={<X size={18} />} onClick={() => router.push("/parties")} />
        </div>
      </div>

      <BalanceCard balance={Number(p.balance ?? 0)} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card title="Primary Details" className="border-gray-100">
            <Descriptions column={{ xs: 1, md: 2 }} colon={false} size="small">
              <Descriptions.Item label="Contact">{contactName || dash}</Descriptions.Item>
              <Descriptions.Item label="Company">{p.company_name || dash}</Descriptions.Item>
              <Descriptions.Item label="Email">{p.email || dash}</Descriptions.Item>
              <Descriptions.Item label="Work phone">{p.work_phone || dash}</Descriptions.Item>
              <Descriptions.Item label="Mobile">{p.mobile || dash}</Descriptions.Item>
            </Descriptions>
            {p.notes && (
              <div className="mt-4 border-t border-gray-100 pt-4">
                <div className="text-xs text-gray-400">Remarks</div>
                <div className="mt-0.5 whitespace-pre-wrap text-sm text-gray-600">{p.notes}</div>
              </div>
            )}
          </Card>

          <Card title="Address" className="border-gray-100">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div>
                <div className="mb-1 text-xs text-gray-400">Billing address</div>
                <AddressBlock address={p.billing_address} />
              </div>
              <div>
                <div className="mb-1 text-xs text-gray-400">Shipping address</div>
                <AddressBlock address={p.shipping_address} />
              </div>
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card title="Other Details" className="border-gray-100">
            <Descriptions column={1} colon={false} size="small">
              <Descriptions.Item label="Currency">{p.currency || dash}</Descriptions.Item>
              <Descriptions.Item label="Payment terms">{termLabel(p.payment_term_days)}</Descriptions.Item>
              <Descriptions.Item label="NTN">{p.ntn || dash}</Descriptions.Item>
              {p.type === "individual" ? (
                <Descriptions.Item label="CNIC">{p.cnic || dash}</Descriptions.Item>
              ) : (
                <Descriptions.Item label="STRN">{p.strn || dash}</Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        </div>
      </div>
    </div>
  );
}
