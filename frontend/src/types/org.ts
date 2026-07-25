import type { Address } from "./party";
import type { RoleSummary } from "./rbac";
import type { User } from "./user";

export interface Organization {
  id: number;
  name: string;
  slug: string;
  currency: string;
  industry: string | null;
  country: string;
  ntn: string | null;
  strn: string | null;
  cnic: string | null;
  address: Address | null;
  fiscal_year_start_month: number;
  logo_url: string | null;
  theme: "light" | "dark";
  accent_color: string;
  keep_branding: boolean;
  fbr_enabled: boolean;
  fbr_environment: "sandbox" | "production";
  fbr_province: string | null;
  fbr_sandbox_configured: boolean;
  fbr_production_configured: boolean;
  created_at: string;
}

export interface OrgMembership {
  org_id: number;
  is_owner: boolean;
  organization: Organization;
  role: RoleSummary;
}

export interface Member {
  id: number;
  is_owner: boolean;
  user: User;
  role: RoleSummary;
}
