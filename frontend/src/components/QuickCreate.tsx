"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Dropdown } from "antd";
import { CirclePlus, Plus } from "lucide-react";

interface QuickItem {
  label: string;
  href: string;
}

const SECTIONS: { title: string; items: QuickItem[] }[] = [
  {
    title: "General",
    items: [
      { label: "Add User", href: "/settings/users" },
      { label: "Item", href: "/items" },
      { label: "Composite Items", href: "/items" },
    ],
  },
  {
    title: "Inventory",
    items: [
      { label: "Inventory Adjustments", href: "/inventory" },
      { label: "Packages", href: "/inventory" },
      { label: "Shipment", href: "/inventory" },
      { label: "Transfer Orders", href: "/inventory" },
      { label: "Move Orders", href: "/inventory" },
    ],
  },
  {
    title: "Sales",
    items: [
      { label: "Customer", href: "/sales/customers" },
      { label: "Invoice", href: "/sales/invoices" },
      { label: "Sales Receipt", href: "/sales/receipts" },
      { label: "Sales Order", href: "/sales/orders" },
      { label: "Customer Payment", href: "/sales/payments-received" },
      { label: "Credit Notes", href: "/sales/credit-notes" },
    ],
  },
  {
    title: "Purchases",
    items: [
      { label: "Vendor", href: "/purchases/vendors" },
      { label: "Bill", href: "/purchases/bills" },
      { label: "Purchase Order", href: "/purchases/orders" },
      { label: "Purchase Receive", href: "/purchases/orders" },
      { label: "Vendor Payment", href: "/purchases/payments-made" },
    ],
  },
];

export function QuickCreate() {
  const router = useRouter();
  const [open, setOpen] = useState(false);

  const go = (href: string) => {
    setOpen(false);
    router.push(href);
  };

  const panel = (
    <div
      className="grid max-h-[calc(100vh-88px)] w-[calc(100vw-24px)] grid-cols-2 gap-3 overflow-y-auto rounded-lg border border-gray-100 bg-white p-4 shadow-xl sm:w-auto sm:min-w-[640px] sm:gap-6 sm:p-5 md:grid-cols-4 md:min-w-[720px]"
    >
      {SECTIONS.map((section) => (
        <div key={section.title}>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
            {section.title}
          </div>
          <ul className="space-y-0.5">
            {section.items.map((item) => (
              <li key={item.label}>
                <button
                  type="button"
                  onClick={() => go(item.href)}
                  className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm text-gray-700 hover:bg-gray-50 hover:text-gray-900"
                >
                  <CirclePlus size={14} className="text-gray-400" />
                  {item.label}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );

  return (
    <Dropdown
      open={open}
      onOpenChange={setOpen}
      trigger={["click"]}
      placement="bottomRight"
      popupRender={() => panel}
    >
      <Button type="primary" icon={<Plus size={18} />} />
    </Dropdown>
  );
}
