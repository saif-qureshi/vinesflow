"use client";

import { useState } from "react";
import {
  Alert,
  App,
  Button,
  Card,
  Checkbox,
  Progress,
  Result,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  ArrowLeft,
  BadgeCheck,
  FileCheck2,
  FlaskConical,
  KeyRound,
  PlayCircle,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";

import {
  useOrganization,
  useRunOrganizationFbrSandboxTests,
} from "@/hooks/useSuperAdmin";
import { apiErrorMessage } from "@/lib/api";
import {
  FBR_SANDBOX_SCENARIOS,
  type FbrSandboxScenarioCode,
} from "@/lib/fbrSandboxScenarios";
import type { FbrSandboxTestResult } from "@/types";

const allScenarioCodes = FBR_SANDBOX_SCENARIOS.map((scenario) => scenario.code);
const scenarioGroups = [
  { title: "Core sales", description: "Standard, reduced, exempt and zero-rated goods", from: 1, to: 8 },
  { title: "Industry sales", description: "Sector-specific goods and services", from: 9, to: 18 },
  { title: "Special supplies", description: "Special regimes and notified supplies", from: 19, to: 25 },
  { title: "Retail sales", description: "Standard, third-schedule and reduced retail", from: 26, to: 28 },
].map((group) => ({
  ...group,
  scenarios: FBR_SANDBOX_SCENARIOS.filter((scenario) => {
    const number = Number(scenario.code.slice(2));
    return number >= group.from && number <= group.to;
  }),
}));

export default function OrganizationFbrSandboxTestsPage() {
  const params = useParams<{ id: string }>();
  const organizationId = Number(params.id);
  const { data: organization, isLoading, isError } = useOrganization(organizationId);
  const runTests = useRunOrganizationFbrSandboxTests(organizationId);
  const [selected, setSelected] = useState<FbrSandboxScenarioCode[]>(["SN001"]);
  const [result, setResult] = useState<FbrSandboxTestResult | null>(null);
  const router = useRouter();
  const { message } = App.useApp();

  if (isLoading) {
    return (
      <div className="flex min-h-80 items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }
  if (isError || !organization) {
    return <Result status="404" title="Organization not found" />;
  }

  const sandboxReady = organization.fbr_sandbox_configured;
  const selectionPercent = Math.round((selected.length / FBR_SANDBOX_SCENARIOS.length) * 100);

  const toggleScenario = (code: FbrSandboxScenarioCode, checked: boolean) => {
    setSelected((current) =>
      checked ? [...new Set([...current, code])] : current.filter((value) => value !== code),
    );
  };

  const run = async () => {
    if (!selected.length) {
      message.warning("Select at least one scenario");
      return;
    }
    try {
      const nextResult = await runTests.mutateAsync(selected);
      setResult(nextResult);
      if (nextResult.ok) {
        message.success("All selected sandbox scenarios passed");
      } else {
        message.error(`${nextResult.failed} sandbox scenario tests failed`);
      }
    } catch (error) {
      message.error(apiErrorMessage(error, "Could not run FBR sandbox tests"));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div className="flex items-start gap-3">
          <Button
            type="text"
            icon={<ArrowLeft size={19} />}
            onClick={() => router.push(`/organizations/${organization.id}`)}
            aria-label="Back to organization"
          />
          <div>
            <Typography.Title level={2} className="!mb-1 !text-3xl">
              FBR sandbox tests
            </Typography.Title>
            <Typography.Text type="secondary">
              Run official FBR sandbox scenarios for {organization.name}.
            </Typography.Text>
          </div>
        </div>
        <Button onClick={() => router.push(`/organizations/${organization.id}`)}>
          Organization details
        </Button>
      </div>

      <Card
        title={
          <Space>
            <FlaskConical size={18} className="text-teal-700" />
            Sandbox readiness
          </Space>
        }
        className="overflow-hidden border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.05)]"
      >
        <div className="grid gap-4 md:grid-cols-3">
          <div className="flex items-center gap-4 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
            <div className="rounded-xl bg-slate-200 p-3 text-slate-700">
              <KeyRound size={20} />
            </div>
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Sandbox token</div>
              <div className="mt-1 flex items-center gap-2 font-semibold text-slate-900">
                <span
                  className={`h-2 w-2 rounded-full ${sandboxReady ? "bg-emerald-500" : "bg-amber-500"}`}
                />
                {sandboxReady ? "Configured" : "Required"}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
            <div className="rounded-xl bg-slate-200 p-3 text-slate-700">
              <FlaskConical size={20} />
            </div>
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Environment</div>
              <div className="mt-1 font-semibold capitalize text-slate-900">
                {organization.fbr_environment}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
            <div className="rounded-xl bg-slate-200 p-3 text-slate-700">
              <BadgeCheck size={20} />
            </div>
            <div className="min-w-0">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Seller registration</div>
              <div className="mt-1 truncate font-semibold text-slate-900">
                {organization.cnic || organization.ntn || organization.strn || "Not configured"}
              </div>
            </div>
          </div>
        </div>
        {!sandboxReady && (
          <Alert
            className="mt-4"
            type="warning"
            showIcon
            message="A sandbox token is required"
            description="Add the organization’s FBR sandbox token on its edit page before running scenarios."
            action={
              <Button
                size="small"
                onClick={() => router.push(`/organizations/${organization.id}/edit`)}
              >
                Edit organization
              </Button>
            }
          />
        )}
      </Card>

      <Card
        title={
          <Space>
            <ShieldCheck size={18} className="text-teal-700" />
            Scenario selection
          </Space>
        }
        extra={
          <Space wrap>
            <Button
              size="small"
              icon={<ShieldCheck size={15} />}
              disabled={selected.length === allScenarioCodes.length || runTests.isPending}
              onClick={() => setSelected([...allScenarioCodes])}
            >
              Select all
            </Button>
            <Button
              size="small"
              disabled={runTests.isPending}
              onClick={() => {
                setSelected(["SN001"]);
                setResult(null);
              }}
            >
              Reset
            </Button>
          </Space>
        }
        className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.05)]"
      >
        <div className="mb-5 rounded-xl bg-slate-50 p-4">
          <div className="mb-2 flex items-center justify-between gap-4">
            <div>
              <div className="font-semibold text-slate-900">Test coverage</div>
              <div className="mt-0.5 text-xs text-slate-500">
                Choose only the scenarios relevant to this organization.
              </div>
            </div>
            <div className="shrink-0 text-sm font-semibold text-teal-700">
              {selected.length} / {FBR_SANDBOX_SCENARIOS.length}
            </div>
          </div>
          <Progress percent={selectionPercent} showInfo={false} strokeColor="#0f8a7c" />
        </div>

        <div className="grid gap-4 xl:grid-cols-2 2xl:grid-cols-4">
          {scenarioGroups.map((group) => (
            <section key={group.title} className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50/60">
              <div className="border-b border-slate-200 bg-white px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-semibold text-slate-900">{group.title}</div>
                  <Tag className="!m-0">{group.scenarios.length}</Tag>
                </div>
                <div className="mt-1 text-xs text-slate-500">{group.description}</div>
              </div>
              <div className="grid gap-2 p-3">
                {group.scenarios.map((scenario) => {
                  const checked = selected.includes(scenario.code);
                  return (
                    <label
                      key={scenario.code}
                      htmlFor={`scenario-${scenario.code}`}
                      className={`flex min-h-14 cursor-pointer items-start gap-3 rounded-lg border px-3 py-2.5 transition ${
                        checked
                          ? "border-teal-500 bg-white ring-1 ring-teal-500/20"
                          : "border-slate-200 bg-white hover:border-slate-300"
                      } ${!sandboxReady || runTests.isPending ? "cursor-not-allowed opacity-60" : ""}`}
                    >
                      <Checkbox
                        id={`scenario-${scenario.code}`}
                        checked={checked}
                        disabled={!sandboxReady || runTests.isPending}
                        onChange={(event) => toggleScenario(scenario.code, event.target.checked)}
                        className="!mt-0.5"
                      />
                      <span className="min-w-0">
                        <span className="block text-xs font-bold tracking-wide text-teal-700">
                          {scenario.code}
                        </span>
                        <span className="mt-0.5 block text-sm leading-snug text-slate-700">
                          {scenario.label}
                        </span>
                      </span>
                    </label>
                  );
                })}
              </div>
            </section>
          ))}
        </div>

        <div className="mt-6 flex flex-col justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-center">
          <div>
            <div className="font-semibold text-slate-900">Ready to test</div>
            <div className="mt-1 text-xs text-slate-500">
              FBR receives one sandbox invoice for each selected scenario. Results are not stored.
            </div>
          </div>
          <Button
            type="primary"
            size="large"
            icon={
              runTests.isPending ? (
                <RefreshCw className="animate-spin" size={17} />
              ) : (
                <PlayCircle size={17} />
              )
            }
            disabled={!sandboxReady || !selected.length}
            loading={runTests.isPending}
            onClick={() => void run()}
          >
            {runTests.isPending
              ? "Running scenarios"
              : `Run ${selected.length} scenario${selected.length === 1 ? "" : "s"}`}
          </Button>
        </div>
      </Card>

      <Card
        title={
          <Space>
            <FileCheck2 size={18} className="text-teal-700" />
            Current run result
          </Space>
        }
        extra={
          result ? (
            <Tag>
              {result.passed}/{result.total} passed
            </Tag>
          ) : null
        }
        className="border-slate-200 shadow-[0_1px_3px_rgba(15,23,42,0.05)]"
      >
        {!result ? (
          <div className="flex flex-col items-center py-12 text-center">
            <div className="rounded-2xl bg-slate-100 p-4 text-slate-400">
              <FileCheck2 size={28} />
            </div>
            <div className="mt-4 font-semibold text-slate-800">No test run yet</div>
            <div className="mt-1 max-w-md text-sm text-slate-500">
              Select scenarios above and run the sandbox test to see FBR validation results here.
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="text-xs uppercase tracking-wide text-slate-500">Total</div>
                <div className="mt-1 text-2xl font-semibold text-slate-900">{result.total}</div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" /> Passed
                </div>
                <div className="mt-1 text-2xl font-semibold text-slate-900">{result.passed}</div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500">
                  <span className="h-2 w-2 rounded-full bg-red-500" /> Failed
                </div>
                <div className="mt-1 text-2xl font-semibold text-slate-900">{result.failed}</div>
              </div>
            </div>
            <Table
              rowKey="code"
              pagination={false}
              dataSource={result.scenarios}
              scroll={{ x: 900 }}
              columns={[
              {
                title: "Scenario",
                key: "scenario",
                render: (_, scenario) => (
                  <div>
                    <div className="font-medium">{scenario.code}</div>
                    <div className="text-xs text-slate-500">{scenario.label}</div>
                  </div>
                ),
              },
              {
                title: "Status",
                dataIndex: "status",
                render: (status: "passed" | "failed") => (
                  <span className="inline-flex items-center gap-2 text-sm capitalize text-slate-700">
                    <span
                      className={`h-2 w-2 rounded-full ${status === "passed" ? "bg-emerald-500" : "bg-red-500"}`}
                    />
                    {status}
                  </span>
                ),
              },
              { title: "HTTP", dataIndex: "http_status_code", render: (value) => value ?? "—" },
              { title: "FBR", dataIndex: "fbr_status_code", render: (value) => value ?? "—" },
              { title: "Invoice", dataIndex: "invoice_number", render: (value) => value ?? "—" },
                {
                  title: "Errors",
                  dataIndex: "errors",
                  render: (errors: string[]) => (errors.length ? errors.join("; ") : "—"),
                },
              ]}
            />
          </div>
        )}
      </Card>
    </div>
  );
}
