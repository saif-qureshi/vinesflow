"use client";

import { useEffect, useMemo, useState } from "react";
import { App, ConfigProvider, Spin } from "antd";
import { QueryClientProvider } from "@tanstack/react-query";

import { requestAccessToken } from "@/lib/api";
import { makeQueryClient } from "@/lib/queryClient";
import { useAppTheme, useMe } from "@/hooks/useSession";
import { useSessionStore } from "@/stores/session";
import { buildAntdTheme } from "@/theme/tokens";
import { AppLoaderIndicator } from "@/components/ui/AppLoader";

function SessionSync() {
  const { data } = useMe();
  const currentOrgId = useSessionStore((s) => s.currentOrgId);
  const setCurrentOrgId = useSessionStore((s) => s.setCurrentOrgId);

  useEffect(() => {
    if (!data) return;
    const valid = data.memberships.some((m) => m.org_id === currentOrgId);
    if (!valid) setCurrentOrgId(data.memberships[0]?.org_id ?? null);
  }, [data, currentOrgId, setCurrentOrgId]);

  return null;
}

function AuthBootstrap({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let mounted = true;
    (async () => {
      if (!useSessionStore.getState().accessToken) {
        await requestAccessToken();
      }
      if (mounted) setReady(true);
    })();
    return () => {
      mounted = false;
    };
  }, []);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <>
      <SessionSync />
      {children}
    </>
  );
}

function ThemedApp({ children }: { children: React.ReactNode }) {
  const { theme, accent } = useAppTheme();
  const themeConfig = useMemo(() => buildAntdTheme(theme, accent), [theme, accent]);

  return (
    <ConfigProvider theme={themeConfig} spin={{ indicator: <AppLoaderIndicator /> }}>
      <App>
        <AuthBootstrap>{children}</AuthBootstrap>
      </App>
    </ConfigProvider>
  );
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(makeQueryClient);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemedApp>{children}</ThemedApp>
    </QueryClientProvider>
  );
}
