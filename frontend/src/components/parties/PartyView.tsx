"use client";

import { useRouter } from "next/navigation";
import { Descriptions, Spin } from "antd";
import { Pencil, Plus, Trash2, X } from "lucide-react";

import { App, Avatar, Button, Card, Popconfirm, Tag, Typography } from "@/components/ui";
import { useCan } from "@/hooks/useSession";
import { useDeleteParty, useParty, useUpdateParty } from "@/hooks/useParties";
import { apiErrorMessage } from "@/lib/api";
import type { Address, PartyRole } from "@/types";
import { PAYMENT_TERMS, basePath, otherRole, roleLabel } from "./constants";

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

function termLabel(days: number | null) {
  if (days == null) return dash;
  return PAYMENT_TERMS.find((t) => t.value === days)?.label ?? `Net ${days}`;
}

export function PartyView({ role, id }: { role: PartyRole; id: number }) {
  const router = useRouter();
  const { message } = App.useApp();
  const can = useCan();
  const update = useUpdateParty();
  const del = useDeleteParty();
  const { data: p, isLoading } = useParty(id);

  const label = roleLabel(role);
  const base = basePath(role);
  const other = otherRole(role);
  const otherLabel = roleLabel(other);

  if (isLoading || !p) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  const hasOtherRole = other === "vendor" ? p.is_vendor : p.is_customer;

  const enableOther = async () => {
    try {
      await update.mutateAsync({
        id: p.id,
        payload: other === "vendor" ? { is_vendor: true } : { is_customer: true },
      });
      message.success(`Enabled as ${otherLabel.toLowerCase()}`);
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  const remove = async () => {
    try {
      if (hasOtherRole) {
        await update.mutateAsync({
          id: p.id,
          payload: role === "customer" ? { is_customer: false } : { is_vendor: false },
        });
      } else {
        await del.mutateAsync(p.id);
      }
      message.success(`${label} removed`);
      router.push(base);
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
          {can("parties:update") && !hasOtherRole && (
            <Button icon={<Plus size={16} />} loading={update.isPending} onClick={enableOther}>
              Enable as {otherLabel.toLowerCase()}
            </Button>
          )}
          {can("parties:update") && (
            <Button icon={<Pencil size={16} />} onClick={() => router.push(`${base}/${p.id}/edit`)}>
              Edit
            </Button>
          )}
          {can("parties:delete") && (
            <Popconfirm
              title={`Remove this ${role}?`}
              description={hasOtherRole ? `Kept as a ${other}.` : "This cannot be undone."}
              okText="Remove"
              okButtonProps={{ danger: true, loading: del.isPending }}
              onConfirm={remove}
            >
              <Button danger icon={<Trash2 size={16} />}>
                Remove
              </Button>
            </Popconfirm>
          )}
          <Button type="text" icon={<X size={18} />} onClick={() => router.push(base)} />
        </div>
      </div>

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
