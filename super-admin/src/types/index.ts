export interface ApiEnvelope<T> {
  success: boolean;
  data: T | null;
  error: { message: string; details?: Array<{ msg?: string }> } | null;
}

export interface AccessToken {
  access_token: string;
  token_type: string;
}

export interface SuperAdmin {
  id: number;
  email: string;
  full_name: string | null;
}

export interface DashboardSummary {
  organizations: number;
  active_organizations: number;
  inactive_organizations: number;
  organization_users: number;
  new_organizations_30d: number;
  fbr_enabled_organizations: number;
  tax_identity_organizations: number;
  fbr_configuration_issues: number;
  recent_organizations: DashboardOrganization[];
  activity_14d: DashboardActivityPoint[];
  fbr_invoice_activity_14d: DashboardFbrInvoiceActivityPoint[];
}

export interface DashboardActivityPoint {
  date: string;
  customer_logins: number;
  organizations_created: number;
}

export interface DashboardFbrInvoiceActivityPoint {
  date: string;
  submitted: number;
  draft: number;
  failed: number;
}

export interface DashboardOrganization {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  owner_email: string;
  member_count: number;
  tax_identity_configured: boolean;
  fbr_enabled: boolean;
  fbr_ready: boolean;
  created_at: string;
}

export interface Organization {
  id: number;
  name: string;
  slug: string;
  currency: string;
  country: string;
  industry: string | null;
  is_active: boolean;
  owner_name: string | null;
  owner_email: string;
  member_count: number;
  fiscal_year_start_month: number;
  created_at: string;
}

export interface OrganizationAddress {
  attention: string | null;
  line1: string | null;
  line2: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  postal_code: string | null;
  phone: string | null;
}

export interface OrganizationMember {
  membership_id: number;
  user_id: number;
  full_name: string | null;
  email: string;
  role_name: string;
  role_slug: string;
  is_owner: boolean;
  is_active: boolean;
}

export interface OrganizationDetail extends Organization {
  ntn: string | null;
  strn: string | null;
  cnic: string | null;
  address: OrganizationAddress | null;
  logo_key: string | null;
  logo_url: string | null;
  fbr_enabled: boolean;
  fbr_environment: "sandbox" | "production";
  fbr_province: string | null;
  fbr_sandbox_configured: boolean;
  fbr_production_configured: boolean;
  members: OrganizationMember[];
}

export interface OrganizationPage {
  items: Organization[];
  total: number;
  page: number;
  page_size: number;
}

export interface OrganizationOnboardInput {
  name: string;
  owner_email: string;
  owner_password: string;
  owner_full_name?: string;
  currency: string;
  country: string;
  industry?: string;
  fiscal_year_start_month: number;
}

export interface OrganizationUpdateInput {
  name: string;
  currency: string;
  country: string;
  industry?: string;
  ntn?: string;
  strn?: string;
  cnic?: string;
  address?: Partial<OrganizationAddress> | null;
  logo_key?: string;
  fbr_enabled?: boolean;
  fbr_environment?: "sandbox" | "production";
  fbr_province?: string;
  fbr_sandbox_token?: string;
  fbr_production_token?: string;
  fiscal_year_start_month: number;
  is_active: boolean;
}

export interface FbrSandboxScenarioResult {
  code: string;
  label: string;
  status: "passed" | "failed";
  http_status_code: number | null;
  fbr_status_code: string | null;
  invoice_number: string | null;
  errors: string[];
}

export interface FbrSandboxTestResult {
  ok: boolean;
  total: number;
  passed: number;
  failed: number;
  scenarios: FbrSandboxScenarioResult[];
  started_at: string;
  completed_at: string;
}

export interface OrganizationOwnerPasswordResult {
  owner_email: string;
  message: string;
}

export interface UploadedFile {
  storage_key: string;
  url: string;
}
