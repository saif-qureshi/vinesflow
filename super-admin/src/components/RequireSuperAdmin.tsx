"use client";

import { useEffect } from "react";
import { Spin } from "antd";
import { useRouter } from "next/navigation";

import { useSuperAdmin } from "@/hooks/useSuperAdmin";
import { useSessionStore } from "@/stores/session";

export function RequireSuperAdmin({ children }: { children: React.ReactNode }) {
  const token = useSessionStore((state) => state.accessToken);
  const clear = useSessionStore((state) => state.clear);
  const { data, isLoading, isError } = useSuperAdmin();
  const router = useRouter();

  useEffect(() => {
    if (!token || isError) {
      if (isError) clear();
      router.replace("/login");
    }
  }, [token, isError, clear, router]);

  if (!token || isLoading || !data) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <Spin size="large" />
      </div>
    );
  }
  return children;
}
