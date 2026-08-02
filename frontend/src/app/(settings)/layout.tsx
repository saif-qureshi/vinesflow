"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Button, Divider, Input, Layout, Menu, Typography, type MenuProps } from "antd";
import { Boxes, Building2, ChevronLeft, Search, ShieldCheck, SlidersHorizontal, UserRound } from "lucide-react";

import { AppFooter } from "@/components/AppFooter";
import { Logo } from "@/components/Logo";
import { RequireAuth } from "@/components/RequireAuth";
import { useCan, useSession } from "@/hooks/useSession";

const { Sider, Content, Header } = Layout;

interface Leaf {
  key: string;
  label: string;
  permission?: string;
}

interface Group {
  key: string;
  label: string;
  icon: React.ReactNode;
  children: Leaf[];
}

const SECTIONS: { heading: string; groups: Group[] }[] = [
  {
    heading: "Organization Settings",
    groups: [
      {
        key: "organization",
        label: "Organization",
        icon: <Building2 size={16} />,
        children: [
          { key: "/settings/organization/profile", label: "Profile" },
          { key: "/settings/organization/branding", label: "Branding" },
          { key: "/settings/organization/fbr", label: "FBR e-Invoicing" },
          { key: "/settings/organization/subscription", label: "Subscription" },
        ],
      },
      {
        key: "users-roles",
        label: "Users & Roles",
        icon: <ShieldCheck size={16} />,
        children: [
          { key: "/settings/users", label: "Users", permission: "users:read" },
          { key: "/settings/roles", label: "Roles", permission: "roles:read" },
        ],
      },
      {
        key: "customization",
        label: "Customization",
        icon: <SlidersHorizontal size={16} />,
        children: [
          { key: "/settings/customization/transaction-numbers", label: "Transaction Number Series" },
        ],
      },
    ],
  },
  {
    heading: "Master Data",
    groups: [
      {
        key: "master-data",
        label: "Items",
        icon: <Boxes size={16} />,
        children: [
          { key: "/settings/master-data/categories", label: "Categories", permission: "products:read" },
          { key: "/settings/master-data/units", label: "Units", permission: "products:read" },
        ],
      },
    ],
  },
  {
    heading: "My Account",
    groups: [
      {
        key: "account",
        label: "Account",
        icon: <UserRound size={16} />,
        children: [{ key: "/settings/account", label: "Profile" }],
      },
    ],
  },
];

function SettingsShell({ children }: { children: React.ReactNode }) {
  const { currentMembership } = useSession();
  const can = useCan();
  const router = useRouter();
  const pathname = usePathname();

  const items: MenuProps["items"] = useMemo(
    () =>
      SECTIONS.map((section) => ({
        key: section.heading,
        type: "group",
        label: section.heading.toUpperCase(),
        children: section.groups
          .map((group) => {
            const children = group.children.filter((c) => !c.permission || can(c.permission));
            if (!children.length) return null;
            return {
              key: group.key,
              label: group.label,
              icon: group.icon,
              children: children.map((c) => ({ key: c.key, label: c.label })),
            };
          })
          .filter(Boolean),
      })),
    [can],
  );

  const parentKey = useMemo(() => {
    for (const section of SECTIONS) {
      for (const group of section.groups) {
        if (group.children.some((c) => c.key === pathname)) return group.key;
      }
    }
    return "organization";
  }, [pathname]);
  const [openKeys, setOpenKeys] = useState<string[]>([parentKey]);
  useEffect(() => setOpenKeys((prev) => Array.from(new Set([...prev, parentKey]))), [parentKey]);

  const close = () => router.push("/dashboard");

  return (
    <Layout className="h-screen">
      <Header
        style={{ paddingInline: 12 }}
        className="flex items-center gap-3 border-b border-gray-200"
      >
        <Logo size={28} priority />
        <Divider orientation="vertical" className="!mx-0 !h-7" />
        <Button icon={<ChevronLeft size={18} />} onClick={close} />
        <div className="leading-tight">
          <div className="text-sm font-semibold">All Settings</div>
          <Typography.Text type="secondary" className="text-xs">
            {currentMembership?.organization.name}
          </Typography.Text>
        </div>
        <Input
          prefix={<Search size={16} className="text-gray-400" />}
          placeholder="Search settings"
          variant="filled"
          className="mx-auto max-w-md"
        />
      </Header>
      <Layout>
        <Sider width={230} theme="light" className="overflow-auto border-r border-gray-100">
          <Menu
            mode="inline"
            items={items}
            selectedKeys={[pathname]}
            openKeys={openKeys}
            onOpenChange={(keys) => setOpenKeys(keys as string[])}
            onClick={({ key }) => router.push(key)}
            className="!border-r-0 py-2"
          />
        </Sider>
        <Content
          style={{ background: "var(--settings-content)" }}
          className="flex flex-col overflow-auto"
        >
          <div className="flex-1 p-8">{children}</div>
          <AppFooter />
        </Content>
      </Layout>
    </Layout>
  );
}

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <SettingsShell>{children}</SettingsShell>
    </RequireAuth>
  );
}
