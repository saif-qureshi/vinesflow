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
  fiscal_year_start_month: number;
  is_active: boolean;
}
