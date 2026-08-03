"use client";

import { ConfigProvider, Typography } from "antd";
import { BarChart3, Boxes, PackageCheck, ShoppingCart } from "lucide-react";

import { Logo } from "@/components/Logo";

export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#0f766e",
          colorLink: "#0f766e",
        },
      }}
    >
      <main className="flex min-h-screen items-center justify-center bg-slate-200/80 p-3 sm:p-8">
      <div className="grid w-full max-w-5xl overflow-hidden rounded-2xl bg-white shadow-2xl shadow-slate-400/25 md:min-h-[620px] md:grid-cols-[48%_52%]">
        <section className="flex items-center px-5 py-8 sm:px-12 sm:py-10 lg:px-16">
          <div className="mx-auto w-full max-w-sm">
            <div className="mb-8 flex items-center gap-3 sm:mb-10">
              <Logo size={38} priority />
              <span className="text-lg font-semibold tracking-tight text-slate-900">Vineflow</span>
            </div>
            <div className="mb-8">
              <Typography.Title level={2} className="!mb-2 !text-[28px]">
                {title}
              </Typography.Title>
              <Typography.Text type="secondary">{subtitle}</Typography.Text>
            </div>
            {children}
          </div>
        </section>

        <section className="relative hidden overflow-hidden bg-gradient-to-br from-emerald-800 via-emerald-700 to-teal-700 p-10 text-white md:flex md:flex-col md:justify-center">
          <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full border-[48px] border-white/5" />
          <div className="absolute -bottom-28 -left-20 h-80 w-80 rounded-full bg-cyan-300/10 blur-sm" />
          <div className="absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/10 blur-2xl" />

          <div className="relative mx-auto w-full max-w-md">
            <div className="rounded-2xl border border-white/20 bg-white/95 p-4 text-slate-800 shadow-2xl shadow-emerald-950/30 backdrop-blur">
              <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
                <div className="h-2.5 w-2.5 rounded-full bg-rose-400" />
                <div className="h-2.5 w-2.5 rounded-full bg-amber-400" />
                <div className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
                <div className="ml-3 h-2 w-24 rounded-full bg-slate-200" />
              </div>
              <div className="grid grid-cols-[72px_1fr] gap-4">
                <div className="space-y-3 rounded-xl bg-slate-900 p-3">
                  <div className="flex h-8 items-center justify-center rounded-lg bg-emerald-600">
                    <BarChart3 size={15} className="text-white" />
                  </div>
                  <div className="flex h-8 items-center justify-center rounded-lg bg-white/10">
                    <ShoppingCart size={15} className="text-slate-300" />
                  </div>
                  <div className="flex h-8 items-center justify-center rounded-lg bg-white/10">
                    <Boxes size={15} className="text-slate-300" />
                  </div>
                </div>
                <div>
                  <div className="mb-3 grid grid-cols-3 gap-2">
                    {[
                      ["Sales", "2.4m"],
                      ["Orders", "428"],
                      ["Stock", "98%"],
                    ].map(([label, value]) => (
                      <div key={label} className="rounded-lg bg-slate-50 p-2.5">
                        <div className="text-[9px] text-slate-400">{label}</div>
                        <div className="text-sm font-semibold">{value}</div>
                      </div>
                    ))}
                  </div>
                  <div className="rounded-lg border border-slate-100 p-3">
                    <div className="mb-3 flex items-center justify-between">
                      <div>
                        <div className="text-[10px] text-slate-400">Revenue flow</div>
                        <div className="text-xs font-semibold">This month</div>
                      </div>
                      <PackageCheck size={19} className="text-emerald-500" />
                    </div>
                    <div className="flex h-20 items-end gap-2">
                      {[36, 54, 42, 68, 58, 82, 72, 94].map((height, index) => (
                        <div
                          key={index}
                          className="flex-1 rounded-t bg-gradient-to-t from-emerald-700 to-teal-400"
                          style={{ height: `${height}%` }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-10 text-center">
              <h2 className="text-2xl font-semibold tracking-tight">
                One connected flow for your business.
              </h2>
              <p className="mx-auto mt-3 max-w-sm text-sm leading-6 text-emerald-100">
                Manage sales, purchases, inventory, invoicing, and accounting from one workspace.
              </p>
              <div className="mt-6 flex justify-center gap-2">
                <span className="h-1.5 w-6 rounded-full bg-white" />
                <span className="h-1.5 w-1.5 rounded-full bg-white/40" />
                <span className="h-1.5 w-1.5 rounded-full bg-white/40" />
              </div>
            </div>
          </div>
        </section>
      </div>
      </main>
    </ConfigProvider>
  );
}
