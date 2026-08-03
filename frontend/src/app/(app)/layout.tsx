"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  Avatar,
  Badge,
  Button,
  Drawer,
  Dropdown,
  Empty,
  Grid,
  Input,
  Layout,
  Menu,
  Popover,
  Select,
  Tag,
  type MenuProps,
} from "antd";
import {
  BarChart3,
  Bell,
  FolderOpen,
  Landmark,
  LayoutDashboard,
  LogOut,
  Menu as MenuIcon,
  Package,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Settings,
  ShoppingBag,
  ShoppingCart,
  Warehouse,
} from "lucide-react";

import { AppFooter } from "@/components/AppFooter";
import { Logo } from "@/components/Logo";
import { QuickCreate } from "@/components/QuickCreate";
import { RecentActivity } from "@/components/layout/RecentActivity";
import { RequireAuth } from "@/components/RequireAuth";
import { useAppTheme, useLogout, useSession, useSwitchOrg } from "@/hooks/useSession";

const { Header, Sider, Content } = Layout;
const ICON = 18;
const WIDTH = 260;
const COLLAPSED = 72;

const NAV: MenuProps["items"] = [
  { key: "/dashboard", icon: <LayoutDashboard size={ICON} />, label: "Dashboard" },
  { key: "/items", icon: <Package size={ICON} />, label: "Items" },
  {
    key: "inventory",
    icon: <Warehouse size={ICON} />,
    label: "Inventory",
    children: [
      { key: "/inventory", label: "Stock" },
      { key: "/inventory/warehouses", label: "Warehouses" },
    ],
  },
  {
    key: "sales",
    icon: <ShoppingCart size={ICON} />,
    label: "Sales",
    children: [
      { key: "/sales/customers", label: "Customers" },
      { key: "/sales/orders", label: "Sales Orders" },
      { key: "/sales/challans", label: "Delivery Challans" },
      { key: "/sales/invoices", label: "Invoices" },
      { key: "/sales/receipts", label: "Sales Receipts" },
      { key: "/sales/payments-received", label: "Payments Received" },
      { key: "/sales/credit-notes", label: "Credit Notes" },
    ],
  },
  {
    key: "purchases",
    icon: <ShoppingBag size={ICON} />,
    label: "Purchases",
    children: [
      { key: "/purchases/vendors", label: "Vendors" },
      { key: "/purchases/orders", label: "Purchase Orders" },
      { key: "/purchases/receipts", label: "Goods Receipts" },
      { key: "/purchases/bills", label: "Bills" },
      { key: "/purchases/expenses", label: "Expenses" },
      { key: "/purchases/payments-made", label: "Payments Made" },
    ],
  },
  {
    key: "accountant",
    icon: <Landmark size={ICON} />,
    label: "Accountant",
    children: [
      { key: "/accountant/chart-of-accounts", label: "Chart of Accounts" },
      { key: "/accountant/opening-balances", label: "Opening Balances" },
      { key: "/accountant/journals", label: "Manual Journals" },
      { key: "/accountant/periods", label: "Fiscal Periods" },
    ],
  },
  { key: "/reports", icon: <BarChart3 size={ICON} />, label: "Reports" },
  { key: "/documents", icon: <FolderOpen size={ICON} />, label: "Documents" },
];

function Brand({ collapsed }: { collapsed?: boolean }) {
  return (
    <div className="flex h-15 items-center gap-3 px-5 py-4">
      <Logo size={30} priority />
      {!collapsed && (
        <span className="text-base font-semibold text-slate-900 dark:text-white">Vineflow</span>
      )}
    </div>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  const { user, memberships, currentOrgId } = useSession();
  const { theme, accent } = useAppTheme();
  const switchOrg = useSwitchOrg();
  const logout = useLogout();
  const router = useRouter();
  const pathname = usePathname();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.lg;

  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const derivedOpen = useMemo(() => {
    if (pathname.startsWith("/inventory")) return ["inventory"];
    if (pathname.startsWith("/sales")) return ["sales"];
    if (pathname.startsWith("/purchases")) return ["purchases"];
    if (pathname.startsWith("/accountant")) return ["accountant"];
    return [];
  }, [pathname]);
  const [openKeys, setOpenKeys] = useState<string[]>(derivedOpen);
  useEffect(() => setOpenKeys(derivedOpen), [derivedOpen]);

  const navigate = (key: string) => {
    router.push(key);
    setDrawerOpen(false);
  };

  const onLogout = async () => {
    await logout();
    router.replace("/login");
  };

  const userMenu: MenuProps["items"] = [
    { key: "email", label: user?.email, disabled: true },
    { key: "account", icon: <Settings size={15} />, label: "Account settings" },
    { type: "divider" },
    { key: "logout", icon: <LogOut size={15} />, label: "Sign out", danger: true },
  ];

  const onUserMenu: MenuProps["onClick"] = ({ key }) => {
    if (key === "logout") onLogout();
    if (key === "account") router.push("/settings/account");
  };

  const navMenu = (
    <Menu
      theme={theme}
      mode="inline"
      items={NAV}
      selectedKeys={[pathname]}
      openKeys={openKeys}
      onOpenChange={(keys) => setOpenKeys(keys as string[])}
      onClick={({ key }) => navigate(key)}
      className="!border-r-0"
    />
  );

  const notifications = (
    <div className="w-72">
      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="You're all caught up" />
    </div>
  );

  return (
    <Layout className="min-h-screen">
      {!isMobile && (
        <Sider
          theme={theme}
          width={WIDTH}
          collapsedWidth={COLLAPSED}
          collapsed={collapsed}
          trigger={null}
          className="!fixed left-0 top-0 bottom-0 z-20 h-screen border-r border-gray-200 dark:border-slate-800"
        >
          <div className={`flex h-full flex-col ${theme === "dark" ? "dark" : ""}`}>
            <Brand collapsed={collapsed} />
            <div className="flex-1 overflow-auto">{navMenu}</div>
            <div className="flex justify-end border-t border-gray-100 p-2 dark:border-slate-800">
              <Button
                type="text"
                className="text-gray-500 dark:text-slate-300"
                icon={collapsed ? <PanelLeftOpen size={ICON} /> : <PanelLeftClose size={ICON} />}
                onClick={() => setCollapsed((c) => !c)}
              />
            </div>
          </div>
        </Sider>
      )}

      <Drawer
        placement="left"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        styles={{
          body: { padding: 0, background: theme === "dark" ? "#0f172a" : undefined },
          header: { display: "none" },
          wrapper: { width: WIDTH },
        }}
      >
        <div className={theme === "dark" ? "dark h-full" : "h-full"}>
          <Brand />
          {navMenu}
        </div>
      </Drawer>

      <Layout
        className="flex min-w-0 flex-col"
        style={{
          marginLeft: isMobile ? 0 : collapsed ? COLLAPSED : WIDTH,
          transition: "margin-left 0.2s",
          minHeight: "100vh",
        }}
      >
        <Header
          style={{ paddingInline: 8 }}
          className="sticky top-0 z-10 flex min-h-16 items-center gap-2 !leading-normal shadow-sm"
        >
          {isMobile && (
            <Button type="text" icon={<MenuIcon size={ICON} />} onClick={() => setDrawerOpen(true)} />
          )}
          <div className="hidden xl:block">
            <RecentActivity />
          </div>
          <Input
            prefix={<Search size={16} className="text-gray-400" />}
            suffix={
              <kbd className="rounded border border-gray-200 bg-white px-1.5 py-0.5 text-[11px] font-medium text-gray-400">
                ⌘K
              </kbd>
            }
            placeholder="Search…"
            variant="filled"
            className="ml-1 hidden max-w-md xl:block"
          />
          <div className="ml-auto flex min-w-0 flex-1 items-center justify-end gap-1 sm:gap-2 lg:flex-none lg:gap-3">
            <Select
              value={currentOrgId ?? undefined}
              onChange={(v) => switchOrg(v)}
              variant="borderless"
              popupMatchSelectWidth={false}
              className="!w-full max-w-40 sm:!w-52 sm:max-w-none"
              options={memberships.map((m) => ({
                value: m.org_id,
                label: (
                  <span className="flex items-center gap-2">
                    {m.organization.name}
                    <Tag color={m.is_owner ? "gold" : "geekblue"} className="!m-0">
                      {m.role.name}
                    </Tag>
                  </span>
                ),
              }))}
            />
            <QuickCreate />
            <Popover trigger="click" placement="bottomRight" title="Notifications" content={notifications}>
              <Badge dot>
                <Button className="hidden md:inline-flex" type="text" icon={<Bell size={ICON} />} />
              </Badge>
            </Popover>
            <Button
              className="hidden md:inline-flex"
              type="text"
              icon={<Settings size={ICON} />}
              onClick={() => router.push("/settings")}
            />
            <Dropdown menu={{ items: userMenu, onClick: onUserMenu }} trigger={["click"]}>
              <div className="flex shrink-0 cursor-pointer items-center gap-2 pr-1">
                <Avatar src={user?.avatar_url ?? undefined} style={{ backgroundColor: accent }}>
                  {(user?.full_name ?? user?.email ?? "?").charAt(0).toUpperCase()}
                </Avatar>
              </div>
            </Dropdown>
          </div>
        </Header>
        <Content className="flex min-w-0 flex-1 flex-col bg-slate-50">
          <div className="min-w-0 flex-1 p-3 sm:p-6">{children}</div>
          <AppFooter />
        </Content>
      </Layout>
    </Layout>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <Shell>{children}</Shell>
    </RequireAuth>
  );
}
