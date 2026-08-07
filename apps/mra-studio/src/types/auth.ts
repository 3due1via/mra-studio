export type Role = "admin" | "editor" | "viewer";

export type User = {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  is_active: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
};

export type UserInput = {
  email: string;
  display_name: string;
  password: string;
  role: Role;
  must_change_password?: boolean;
};
