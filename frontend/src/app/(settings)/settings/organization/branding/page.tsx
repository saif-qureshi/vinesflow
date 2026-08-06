"use client";

import { useEffect, useState } from "react";
import { ColorPicker, Switch } from "antd";
import { Check, Loader2, Moon, Sun } from "lucide-react";

import { App, PageHeader, Typography } from "@/components/ui";
import { Uploader } from "@/components/ui/Uploader";
import { SettingRow } from "@/components/settings/SettingRow";
import { useCan, useSession } from "@/hooks/useSession";
import { useUpdateOrg } from "@/hooks/useOrg";
import { apiErrorMessage } from "@/lib/api";
import { ACCENT_PRESETS } from "@/theme/tokens";
import type { UploadedFile } from "@/types";

type Patch = Parameters<ReturnType<typeof useUpdateOrg>["mutate"]>[0];

export default function BrandingPage() {
  const { currentMembership } = useSession();
  const can = useCan();
  const { message } = App.useApp();
  const updateOrg = useUpdateOrg();

  const org = currentMembership?.organization;
  const canEdit = can("orgs:update");

  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [accent, setAccent] = useState("#2563eb");
  const [keepBranding, setKeepBranding] = useState(true);
  const [logo, setLogo] = useState<UploadedFile[]>([]);

  useEffect(() => {
    if (!org) return;
    setTheme(org.theme);
    setAccent(org.accent_color);
    setKeepBranding(org.keep_branding);
    setLogo(
      org.logo_key && org.logo_url ? [{ storage_key: org.logo_key, url: org.logo_url }] : [],
    );
  }, [org]);

  // Auto-save: every change persists immediately and applies once refetched.
  const patch = (vars: Patch) =>
    updateOrg.mutate(vars, { onError: (err) => message.error(apiErrorMessage(err)) });

  return (
    <div>
      <PageHeader
        title="Branding"
        description="Changes save automatically."
        actions={
          updateOrg.isPending ? (
            <span className="inline-flex items-center gap-1.5 text-sm text-amber-600">
              <Loader2 size={14} className="animate-spin" /> Saving…
            </span>
          ) : updateOrg.isSuccess ? (
            <span className="inline-flex items-center gap-1.5 text-sm text-green-600">
              <Check size={14} /> All changes saved
            </span>
          ) : undefined
        }
      />

      <div className="mt-2">
        <SettingRow label="Organization Logo" help="Displayed on transaction PDFs and email notifications.">
          <Uploader
            value={logo}
            onChange={(files) => {
              setLogo(files);
              patch({ logo_key: files[0]?.storage_key ?? "" });
            }}
            maxCount={1}
            accept="image/*"
            maxSizeMB={5}
            drag={false}
          />
        </SettingRow>

        <SettingRow label="Appearance" help="Sets the app sidebar to dark or light. The rest of the app stays light.">
          <div className="flex gap-3">
            {(["dark", "light"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                disabled={!canEdit}
                onClick={() => {
                  setTheme(mode);
                  patch({ theme: mode });
                }}
                className={`rounded-xl border p-1.5 transition ${
                  theme === mode ? "border-primary ring-1 ring-primary" : "border-gray-200 dark:border-slate-700"
                }`}
              >
                <div className="flex h-16 w-28 overflow-hidden rounded-md border border-gray-200">
                  {/* sidebar pane — the only part affected */}
                  <div className={`flex w-9 flex-col gap-1 p-1.5 ${mode === "dark" ? "bg-slate-900" : "bg-gray-100"}`}>
                    <div className="h-1.5 w-full rounded" style={{ background: accent }} />
                    <div className={`h-1 w-full rounded ${mode === "dark" ? "bg-slate-600" : "bg-gray-300"}`} />
                    <div className={`h-1 w-full rounded ${mode === "dark" ? "bg-slate-600" : "bg-gray-300"}`} />
                  </div>
                  {/* content — always light */}
                  <div className="flex-1 bg-white p-1.5">
                    <div className="h-1 w-8 rounded bg-gray-200" />
                    <div className="mt-1 h-1 w-10 rounded bg-gray-100" />
                  </div>
                </div>
                <div className="flex items-center justify-center gap-1 py-2 text-xs font-semibold uppercase text-gray-500">
                  {mode === "dark" ? <Moon size={13} /> : <Sun size={13} />}
                  {mode} pane
                </div>
              </button>
            ))}
          </div>
        </SettingRow>

        <SettingRow label="Accent Color" help="Applied to buttons, links, and active navigation.">
          <div className="flex flex-wrap items-center gap-2">
            {ACCENT_PRESETS.map((c) => (
              <button
                key={c.value}
                type="button"
                disabled={!canEdit}
                title={c.name}
                onClick={() => {
                  setAccent(c.value);
                  patch({ accent_color: c.value });
                }}
                className="flex h-9 w-9 items-center justify-center rounded-lg"
                style={{
                  background: c.value,
                  outline: accent === c.value ? "2px solid #0f172a" : "none",
                  outlineOffset: 2,
                }}
              >
                {accent === c.value && <Check size={16} className="text-white" />}
              </button>
            ))}
            <ColorPicker
              value={accent}
              disabled={!canEdit}
              onChangeComplete={(col) => {
                const hex = col.toHexString();
                setAccent(hex);
                patch({ accent_color: hex });
              }}
            >
              <button
                type="button"
                title="Custom color"
                className="h-9 w-9 rounded-lg"
                style={{
                  background:
                    "conic-gradient(from 0deg, #ef4444, #f59e0b, #eab308, #22c55e, #06b6d4, #3b82f6, #8b5cf6, #ef4444)",
                }}
              />
            </ColorPicker>
          </div>
        </SettingRow>

        <SettingRow label="Keep Vineflow branding" help="Show non-obtrusive Vineflow branding on transactional emails and PDFs.">
          <Switch
            checked={keepBranding}
            disabled={!canEdit}
            onChange={(v) => {
              setKeepBranding(v);
              patch({ keep_branding: v });
            }}
          />
        </SettingRow>

        {!canEdit && (
          <Typography.Paragraph type="secondary" className="!mt-4 !mb-0">
            You don&apos;t have permission to edit branding.
          </Typography.Paragraph>
        )}
      </div>
    </div>
  );
}
