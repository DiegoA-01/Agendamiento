export type Role = "superadmin" | "owner" | "admin" | "receptionist" | "professional";
export type Vertical = "barbershop" | "salon" | "nails" | "spa";
export type Language = "es" | "en";
export type TenantStatus = "active" | "suspended";
export type ModuleKey = "booking" | "commissions" | "reports" | "notifications_whatsapp";

export interface Theme {
  primary: string;
  secondary: string;
  background: string;
  surface: string;
  text: string;
}

export interface Me {
  user: { id: string; email: string; full_name: string; phone: string };
  role: Role;
  two_factor_enabled: boolean;
  must_change_password: boolean;
  is_platform_admin: boolean;
  tenant: {
    id: string;
    name: string;
    slug: string;
    vertical: Vertical;
    timezone: string;
    currency: string;
    language: Language;
  } | null;
  theme: Partial<Theme>;
  modules: ModuleKey[];
}

export interface TwoFactorSetup {
  secret: string;
  otpauth_uri: string;
}

export interface Plan {
  id: string;
  name: string;
  modules: ModuleKey[];
  max_professionals: number;
  max_locations: number;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  vertical: Vertical;
  timezone: string;
  currency: string;
  language: Language;
  status: TenantStatus;
  theme: Partial<Theme>;
  created_at: string;
  plan: { id: string; name: string };
}

export interface TenantDetail extends Tenant {
  modules: ModuleKey[];
}

export interface TenantCreated {
  tenant: TenantDetail;
  owner: { email: string; full_name: string };
  temporary_password: string;
}

export interface ModulesInfo {
  available: ModuleKey[];
  enabled: ModuleKey[];
}

export interface Domain {
  id: string;
  host: string;
  kind: "subdomain" | "custom";
  verified: boolean;
  verification_token: string;
  created_at: string;
  instructions: {
    txt: { name: string; value: string };
    cname: { name: string; target: string };
  };
}

export interface DomainVerification {
  verified: boolean;
  txt_ok: boolean;
  cname_ok: boolean;
}

export interface AuditEntry {
  id: string;
  action: string;
  entity: string;
  entity_id: string;
  before: unknown;
  after: unknown;
  ip: string | null;
  created_at: string;
  actor_email: string | null;
  tenant_id: string | null;
  tenant_name: string | null;
}

export interface Paginated<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}

export const MODULE_KEYS: ModuleKey[] = [
  "booking",
  "commissions",
  "reports",
  "notifications_whatsapp",
];
export const VERTICALS: Vertical[] = ["barbershop", "salon", "nails", "spa"];
export const LANGUAGES: Language[] = ["es", "en"];
export const THEME_KEYS: (keyof Theme)[] = [
  "primary",
  "secondary",
  "background",
  "surface",
  "text",
];
