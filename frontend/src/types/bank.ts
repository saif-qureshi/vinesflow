export interface BankOption {
  code: string;
  name: string;
  colour: string;
  logo: string;
}

export interface BankAccount {
  id: number;
  bank_name: string;
  bank_code: string | null;
  account_title: string;
  account_number: string;
  iban: string | null;
  branch: string | null;
  currency: string;
  colour: string | null;
  logo_key: string | null;
  logo_url: string | null;
  account_id: number;
  account_code: string | null;
  balance: string;
  is_active: boolean;
  created_at: string;
}

export interface BankAccountInput {
  bank_name?: string;
  bank_code?: string | null;
  account_title?: string;
  account_number?: string;
  iban?: string | null;
  branch?: string | null;
  colour?: string | null;
  logo_key?: string | null;
  is_active?: boolean;
}
