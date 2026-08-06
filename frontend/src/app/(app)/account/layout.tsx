"use client";

import { useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Menu, type MenuProps } from "antd";
import { KeyRound, UserRound } from "lucide-react";

import { PageHeader } from "@/components/ui";

/** Add a group here and it appears in the sidebar — nothing else to wire. */
const SECTIONS: { key: string; label: string; icon: React.ReactNode }[] = [
  { key: "/account", label: "General", icon: <UserRound size={16} /> },
  { key: "/account/security", label: "Security", icon: <KeyRound size={16} /> },
];

export default function AccountLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  const items: MenuProps["items"] = useMemo(
    () => SECTIONS.map(({ key, label, icon }) => ({ key, label, icon })),
    [],
  );

  // Longest matching prefix, so a nested page still highlights its group.
  const selected = useMemo(() => {
    const match = SECTIONS.map((s) => s.key)
      .filter((key) => pathname === key || pathname.startsWith(`${key}/`))
      .sort((a, b) => b.length - a.length)[0];
    return match ?? "/account";
  }, [pathname]);

  return (
    <div className="space-y-5">
      <PageHeader title="Profile" description="Your personal account details" />
      <div className="flex flex-col gap-6 lg:flex-row">
        <div className="lg:w-56 lg:shrink-0">
          <Menu
            mode="inline"
            items={items}
            selectedKeys={[selected]}
            onClick={({ key }) => router.push(key)}
            className="!border-r-0 rounded-xl border border-gray-100 bg-white p-1"
          />
        </div>
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    </div>
  );
}
