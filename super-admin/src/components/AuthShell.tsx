"use client";

import { Typography } from "antd";

import { Logo } from "@/components/Logo";

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-emerald-50 via-white to-slate-100 p-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mb-3 flex justify-center">
            <Logo size={52} priority />
          </div>
          <Typography.Title level={3} className="!mb-1">
            Super administration
          </Typography.Title>
          <Typography.Text type="secondary">
            Sign in to manage Vineflow organizations
          </Typography.Text>
        </div>
        <div className="rounded-2xl border border-gray-100 bg-white p-8 shadow-xl shadow-slate-200/60">
          {children}
        </div>
      </div>
    </div>
  );
}
