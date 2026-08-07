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
  EllipsisVertical,
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
  UserRound,
  Users,
  Warehouse,
} from "lucide-react";

import { AppFooter } from "@/components/AppFooter";
import { Logo } from "@/components/Logo";
import { RecentActivity } from "@/components/layout/RecentActivity";
import { RequireAuth } from "@/components/RequireAuth";
import { useAppTheme, useCan, useLogout, useSession, useSwitchOrg } from "@/hooks/useSession";

const { Header, Sider, Content } = Layout;
const ICON = 18;
const WIDTH = 260;
const COLLAPSED = 72;

interface NavEntry {
  key: string;
  label: string;
  icon?: React.ReactNode;
  permission?: string;
  children?: NavEntry[];
}

const NAV: NavEntry[] = [
  { key: "/dashboard", icon: <LayoutDashboard size={ICON} />, label: "Dashboard", permission: "reports:read" },
  { key: "/items", icon: <Package size={ICON} />, label: "Items", permission: "products:read" },
  { key: "/parties", icon: <Users size={ICON} />, label: "Parties", permission: "parties:read" },
  {
    key: "inventory",
    icon: <Warehouse size={ICON} />,
    label: "Inventory",
    children: [
      { key: "/inventory", label: "Stock", permission: "inventory:read" },
      { key: "/inventory/warehouses", label: "Warehouses", permission: "inventory:read" },
    ],
  },
  {
    key: "sales",
    icon: <ShoppingCart size={ICON} />,
    label: "Sales",
    children: [
      { key: "/sales/orders", label: "Sales Orders", permission: "sales_orders:read" },
      { key: "/sales/challans", label: "Delivery Challans", permission: "delivery_challans:read" },
      { key: "/sales/invoices", label: "Invoices", permission: "invoices:read" },
      { key: "/sales/receipts", label: "Sales Receipts", permission: "invoices:read" },
      { key: "/sales/payments-received", label: "Payments Received", permission: "payments:read" },
      { key: "/sales/credit-notes", label: "Credit Notes", permission: "credit_notes:read" },
    ],
  },
  {
    key: "purchases",
    icon: <ShoppingBag size={ICON} />,
    label: "Purchases",
    children: [
      { key: "/purchases/orders", label: "Purchase Orders", permission: "purchase_orders:read" },
      { key: "/purchases/receipts", label: "Goods Receipts", permission: "goods_receipts:read" },
      { key: "/purchases/bills", label: "Bills", permission: "bills:read" },
      { key: "/purchases/expenses", label: "Expenses", permission: "expenses:read" },
      { key: "/purchases/payments-made", label: "Payments Made", permission: "payments:read" },
    ],
  },
  {
    key: "accountant",
    icon: <Landmark size={ICON} />,
    label: "Accountant",
    children: [
      { key: "/accountant/chart-of-accounts", label: "Chart of Accounts", permission: "accounting:read" },
      { key: "/accountant/banks", label: "Banks", permission: "accounting:read" },
      { key: "/accountant/cash-book", label: "Cash & Bank Book", permission: "accounting:read" },
      { key: "/accountant/opening-balances", label: "Opening Balances", permission: "accounting:read" },
      { key: "/accountant/journals", label: "Manual Journals", permission: "accounting:read" },
      { key: "/accountant/commissions", label: "Commissions", permission: "payments:read" },
      { key: "/accountant/periods", label: "Fiscal Periods", permission: "accounting:read" },
    ],
  },
  { key: "/reports", icon: <BarChart3 size={ICON} />, label: "Reports", permission: "reports:read" },
  { key: "/documents", icon: <FolderOpen size={ICON} />, label: "Documents", permission: "invoices:read" },
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
  const can = useCan();
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
    { key: "account", icon: <UserRound size={15} />, label: "Profile" },
    { type: "divider" },
    { key: "logout", icon: <LogOut size={15} />, label: "Sign out", danger: true },
  ];

  const onUserMenu: MenuProps["onClick"] = ({ key }) => {
    if (key === "logout") onLogout();
    if (key === "account") router.push("/account");
  };

  // Hide what the member cannot open, the way the settings nav already does.
  const navItems = useMemo<MenuProps["items"]>(() => {
    const visible = (entry: NavEntry): NavEntry | null => {
      if (entry.children) {
        const children = entry.children.map(visible).filter((c): c is NavEntry => !!c);
        return children.length ? { ...entry, children } : null;
      }
      return !entry.permission || can(entry.permission) ? entry : null;
    };
    return NAV.map(visible).filter((e): e is NavEntry => !!e) as MenuProps["items"];
  }, [can]);

  const navMenu = (
    <Menu
      theme={theme}
      mode="inline"
      items={navItems}
      selectedKeys={[pathname.startsWith("/parties") ? "/parties" : pathname]}
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

  const organizationOptions = memberships.map((m) => ({
    value: m.org_id,
    label: (
      <span className="flex min-w-0 items-center gap-2">
        <span className="truncate">{m.organization.name}</span>
        <Tag color={m.is_owner ? "gold" : "geekblue"} className="!m-0 shrink-0">
          {m.role.name}
        </Tag>
      </span>
    ),
  }));

  const mobileTools = (
    <div className="w-64 space-y-2 p-1">
      <div className="px-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
        Organization
      </div>
      <Select
        value={currentOrgId ?? undefined}
        onChange={(value) => switchOrg(value)}
        className="!w-full"
        options={organizationOptions}
      />
      <div className="my-2 border-t border-gray-100" />
      <RecentActivity label="Recent activity" />
      <Popover trigger="click" placement="leftTop" title="Notifications" content={notifications}>
        <Button block className="!justify-start" type="text" icon={<Bell size={ICON} />}>
          Notifications
        </Button>
      </Popover>
      <Button
        block
        className="!justify-start"
        type="text"
        icon={<Settings size={ICON} />}
        onClick={() => router.push("/settings")}
      >
        Settings
      </Button>
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
          className="sticky top-0 z-10 flex min-h-16 items-center gap-2 !leading-normal shadow-sm lg:gap-3"
        >
          {isMobile && (
            <Button type="text" icon={<MenuIcon size={ICON} />} onClick={() => setDrawerOpen(true)} />
          )}
          <div className="hidden lg:block">
            <RecentActivity />
          </div>
          <Input
            prefix={<Search size={16} className="text-gray-400" />}
            suffix={
              <kbd className="hidden rounded border border-gray-200 bg-white px-1.5 py-0.5 text-[11px] font-medium text-gray-400 sm:inline">
                ⌘K
              </kbd>
            }
            placeholder="Search…"
            variant="filled"
            className="!w-full min-w-0 flex-1 lg:ml-1 lg:max-w-md"
          />
          <div className="hidden lg:ml-auto lg:block">
            <Select
              value={currentOrgId ?? undefined}
              onChange={(value) => switchOrg(value)}
              variant="borderless"
              popupMatchSelectWidth={false}
              className="!w-52"
              options={organizationOptions}
            />
          </div>
          <div className="hidden items-center gap-3 lg:flex">
            <Popover trigger="click" placement="bottomRight" title="Notifications" content={notifications}>
              <Badge dot>
                <Button type="text" icon={<Bell size={ICON} />} />
              </Badge>
            </Popover>
            <Button
              type="text"
              icon={<Settings size={ICON} />}
              onClick={() => router.push("/settings")}
            />
          </div>
          <div className="lg:hidden">
            <Popover trigger="click" placement="bottomRight" content={mobileTools}>
              <Button
                type="text"
                aria-label="More actions"
                icon={<EllipsisVertical size={ICON} />}
              />
            </Popover>
          </div>
          <Dropdown menu={{ items: userMenu, onClick: onUserMenu }} trigger={["click"]}>
            <div className="flex shrink-0 cursor-pointer items-center pr-1">
              <Avatar src={user?.avatar_url ?? undefined} style={{ backgroundColor: accent }}>
                {(user?.full_name ?? user?.email ?? "?").charAt(0).toUpperCase()}
              </Avatar>
            </div>
          </Dropdown>
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
