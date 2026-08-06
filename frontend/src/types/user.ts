export interface User {
  id: number;
  email: string;
  full_name: string | null;
  avatar_key: string | null;
  avatar_url: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}
