"use client";

import { useState } from "react";
import { Avatar, Button, Drawer, Dropdown, Grid, Layout, Menu, Typography } from "antd";
import { Building2, LayoutDashboard, LogOut, Menu as MenuIcon, UserRound } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";

import { Logo } from "@/components/Logo";
import { RequireSuperAdmin } from "@/components/RequireSuperAdmin";
import { useAdminLogout, useSuperAdmin } from "@/hooks/useSuperAdmin";

const { Header, Sider, Content } = Layout;
const SIDEBAR_WIDTH = 248;

const navigation = [
  { key: "/dashboard", icon: <LayoutDashboard size={18} />, label: "Dashboard" },
  { key: "/organizations", icon: <Building2 size={18} />, label: "Organizations" },
];

function AdminShell({ children }: { children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { data: admin } = useSuperAdmin();
  const logout = useAdminLogout();
  const pathname = usePathname();
  const router = useRouter();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.lg;

  const navigate = (path: string) => {
    router.push(path);
    setDrawerOpen(false);
  };

  const onLogout = async () => {
    await logout();
    router.replace("/login");
  };

  const sidebar = (
    <div className="flex h-full flex-col bg-white">
      <div className="flex h-15 items-center gap-3 border-b border-slate-100 px-5">
        <Logo size={32} priority />
        <div className="leading-tight">
          <div className="font-semibold text-slate-900">Vineflow</div>
          <div className="text-xs text-slate-500">Super admin</div>
        </div>
      </div>
      <Menu
        mode="inline"
        items={navigation}
        selectedKeys={[pathname]}
        onClick={({ key }) => navigate(key)}
        className="flex-1 !border-r-0 py-3"
      />
    </div>
  );

  return (
    <Layout className="min-h-screen bg-slate-50">
      {!isMobile && (
        <Sider
          width={SIDEBAR_WIDTH}
          theme="light"
          className="!fixed !inset-y-0 !left-0 !z-20 !h-screen border-r border-slate-200 shadow-[1px_0_0_rgba(15,23,42,0.02)]"
        >
          {sidebar}
        </Sider>
      )}
      <Drawer
        placement="left"
        open={isMobile && drawerOpen}
        onClose={() => setDrawerOpen(false)}
        size={SIDEBAR_WIDTH}
        styles={{ body: { padding: 0 } }}
        closable={false}
      >
        {sidebar}
      </Drawer>
      <Layout
        className="flex min-w-0 flex-col"
        style={{ marginLeft: isMobile ? 0 : SIDEBAR_WIDTH, minHeight: "100vh" }}
      >
        <Header className="sticky top-0 z-10 flex items-center border-b border-slate-200 !px-4 shadow-[0_1px_2px_rgba(15,23,42,0.03)] sm:!px-8">
          {isMobile && (
            <Button
              type="text"
              icon={<MenuIcon size={20} />}
              onClick={() => setDrawerOpen(true)}
              className="mr-3"
              aria-label="Open navigation"
            />
          )}
          <div className="leading-tight">
            <Typography.Text className="font-semibold text-slate-800">Super admin</Typography.Text>
            <div className="hidden text-xs text-slate-500 sm:block">Vineflow control center</div>
          </div>
          <Dropdown
            trigger={["click"]}
            menu={{
              items: [
                { key: "email", label: admin?.email, disabled: true },
                { type: "divider" },
                { key: "logout", label: "Sign out", icon: <LogOut size={15} />, danger: true },
              ],
              onClick: ({ key }) => {
                if (key === "logout") void onLogout();
              },
            }}
          >
            <Button type="text" className="ml-auto !h-10 !px-2">
              <Avatar size={30} icon={<UserRound size={16} />} />
              <span className="hidden max-w-48 truncate sm:inline">
                {admin?.full_name || admin?.email}
              </span>
            </Button>
          </Dropdown>
        </Header>
        <Content className="flex-1 bg-slate-50 p-4 sm:p-8">
          <div className="w-full">{children}</div>
        </Content>
      </Layout>
    </Layout>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireSuperAdmin>
      <AdminShell>{children}</AdminShell>
    </RequireSuperAdmin>
  );
}
