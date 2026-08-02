"use client";

import { useEffect, useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { App, ConfigProvider, Spin } from "antd";

import { requestAccessToken } from "@/lib/api";
import { makeQueryClient } from "@/lib/queryClient";
import { useSessionStore } from "@/stores/session";
import { antdTheme } from "@/theme/tokens";

function AuthBootstrap({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let mounted = true;
    (async () => {
      if (!useSessionStore.getState().accessToken) await requestAccessToken();
      if (mounted) setReady(true);
    })();
    return () => {
      mounted = false;
    };
  }, []);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <Spin size="large" />
      </div>
    );
  }
  return children;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(makeQueryClient);
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider theme={antdTheme}>
        <App>
          <AuthBootstrap>{children}</AuthBootstrap>
        </App>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
