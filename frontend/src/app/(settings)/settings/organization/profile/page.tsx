"use client";

import { useEffect, useState } from "react";

import { AddressAutoComplete, App, Input, MaskedInput, MASKS, PageHeader, Select, Tag, Typography } from "@/components/ui";
import { SettingRow, SettingsFooter } from "@/components/settings/SettingRow";
import { useCan, useSession } from "@/hooks/useSession";
import { useUpdateOrg } from "@/hooks/useOrg";
import { apiErrorMessage } from "@/lib/api";
import { COUNTRIES } from "@/lib/countries";
import type { Address } from "@/types";

const CURRENCIES = ["PKR", "USD", "EUR", "GBP", "AED", "SAR", "INR", "CAD", "AUD"].map((c) => ({ value: c, label: c }));
const INDUSTRIES = [
  "Agriculture", "Manufacturing", "Retail", "Wholesale", "Services", "Technology",
  "Construction", "Healthcare", "Education", "Hospitality", "Finance", "Other",
].map((i) => ({ value: i, label: i }));
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const FISCAL_OPTIONS = MONTHS.map((m, i) => ({ value: i + 1, label: `${m} – ${MONTHS[(i + 11) % 12]}` }));

export default function OrganizationProfilePage() {
  const { currentMembership } = useSession();
  const can = useCan();
  const { message } = App.useApp();
  const updateOrg = useUpdateOrg();

  const org = currentMembership?.organization;
  const canEdit = can("orgs:update");

  const [name, setName] = useState("");
  const [industry, setIndustry] = useState<string | undefined>();
  const [currency, setCurrency] = useState("PKR");
  const [fiscalMonth, setFiscalMonth] = useState(7);
  const [ntn, setNtn] = useState("");
  const [strn, setStrn] = useState("");
  const [cnic, setCnic] = useState("");
  const [country, setCountry] = useState("PK");
  const [address, setAddress] = useState<Address>({});

  useEffect(() => {
    if (!org) return;
    setName(org.name);
    setIndustry(org.industry ?? undefined);
    setCurrency(org.currency);
    setFiscalMonth(org.fiscal_year_start_month);
    setNtn(org.ntn ?? "");
    setStrn(org.strn ?? "");
    setCnic(org.cnic ?? "");
    setCountry(org.country);
    setAddress(org.address ?? {});
  }, [org]);

  const startIdx = (fiscalMonth - 1 + 12) % 12;
  const fiscalPeriod = `1 ${MONTHS[startIdx]} – 30 ${MONTHS[(startIdx + 11) % 12]}`;

  const save = async () => {
    if (!name.trim()) {
      message.error("Organization name is required");
      return;
    }
    try {
      await updateOrg.mutateAsync({
        name,
        industry: industry ?? "",
        currency,
        country,
        ntn,
        strn,
        cnic,
        address,
        fiscal_year_start_month: fiscalMonth,
      });
      message.success("Organization updated");
    } catch (err) {
      message.error(apiErrorMessage(err));
    }
  };

  return (
    <div>
      <PageHeader
        title="Organization Profile"
        description={org && <Tag className="!m-0" color="default">ID: {org.id} · {org.slug}</Tag>}
      />

      <div className="mt-2">
        <SettingRow label="Organization Name" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} disabled={!canEdit} className="max-w-md" />
        </SettingRow>

        <SettingRow label="Industry">
          <Select value={industry} onChange={setIndustry} options={INDUSTRIES} showSearch allowClear placeholder="Select industry" disabled={!canEdit} className="max-w-md !w-full md:!w-80" />
        </SettingRow>

        <SettingRow label="Country">
          <Select value={country} onChange={setCountry} options={COUNTRIES.map((c) => ({ value: c.code, label: c.name }))} showSearch optionFilterProp="label" disabled={!canEdit} className="max-w-md !w-full md:!w-80" />
        </SettingRow>

        <SettingRow label="NTN" help="National Tax Number.">
          <MaskedInput mask={MASKS.ntn} value={ntn} onChange={setNtn} placeholder="1234567-8" disabled={!canEdit} className="!w-56" />
        </SettingRow>

        <SettingRow label="STRN" help="Sales Tax Registration Number.">
          <MaskedInput mask={MASKS.strn} value={strn} onChange={setStrn} placeholder="13-digit number" disabled={!canEdit} className="!w-56" />
        </SettingRow>

        <SettingRow label="CNIC" help="For sole proprietors filing under a personal CNIC. FBR prefers this over NTN/STRN.">
          <MaskedInput mask={MASKS.cnic} value={cnic} onChange={setCnic} placeholder="00000-0000000-0" disabled={!canEdit} className="!w-56" />
        </SettingRow>

        <SettingRow label="Base Currency" required>
          <Select value={currency} onChange={setCurrency} options={CURRENCIES} showSearch disabled className="!w-40" />
        </SettingRow>

        <SettingRow label="Fiscal Year" required>
          <div className="flex flex-wrap items-center gap-3">
            <Select value={fiscalMonth} onChange={setFiscalMonth} options={FISCAL_OPTIONS} disabled={!canEdit} className="!w-56" />
            <Tag color="default" className="!m-0">Period: {fiscalPeriod}</Tag>
          </div>
        </SettingRow>

        <SettingRow label="Address">
          <div className="max-w-2xl">
            <AddressAutoComplete value={address} onChange={setAddress} disabled={!canEdit} />
          </div>
        </SettingRow>

        {canEdit ? (
          <SettingsFooter onSave={save} saving={updateOrg.isPending} />
        ) : (
          <Typography.Paragraph type="secondary" className="!mt-4 !mb-0">
            You don&apos;t have permission to edit the organization.
          </Typography.Paragraph>
        )}
      </div>
    </div>
  );
}
