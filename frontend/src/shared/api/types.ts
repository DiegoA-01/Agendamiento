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
  /** Lo que el rol puede hacer, calculado por el backend desde su matriz (spec §5). */
  permissions: Permissions;
}

/** Recursos de la matriz de permisos del backend (`accounts/permissions.py`). */
export type PermissionResource =
  | "company"
  | "staff_services"
  | "schedules"
  | "appointments"
  | "commissions"
  | "plan_modules"
  | "platform";

/** `all` = todos los registros del negocio; `own` = solo los propios. */
export type PermissionScope = "all" | "own";

export type Permissions = Partial<
  Record<PermissionResource, { scope: PermissionScope; actions: string[] }>
>;

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

// --- Panel del negocio: empresa, catálogo y equipo (M4) ----------------------------------------

export interface ImageRef {
  id: string;
  urls: { thumb: string; medium: string; large: string };
}

export interface MediaFile extends ImageRef {
  original_name: string;
  width: number;
  height: number;
}

export const SOCIAL_NETWORKS = ["instagram", "facebook", "tiktok", "whatsapp", "website"] as const;
export type SocialNetwork = (typeof SOCIAL_NETWORKS)[number];

export interface Company {
  legal_name: string;
  trade_name: string;
  tax_id: string;
  address: string;
  city: string;
  phone: string;
  email: string;
  logo: ImageRef | null;
  terms_html: string;
  privacy_html: string;
  cookies_html: string;
  social_links: Partial<Record<SocialNetwork, string>>;
}

export interface BusinessLocation {
  id: string;
  name: string;
  address: string;
  is_default: boolean;
}

export interface Category {
  id: string;
  name: string;
  sort_order: number;
  /** R3: solo un servicio de esta categoría por cita (p. ej. un solo corte). */
  single_choice: boolean;
}

/** Montos como texto decimal (`"30000.00"`): nunca se convierten a número para guardar. */
export interface Service {
  id: string;
  category_id: string;
  name: string;
  description: string;
  duration_min: number;
  buffer_min: number;
  price: string;
  is_active: boolean;
  requires_resource: boolean;
  image: ImageRef | null;
}

export interface Workstation {
  id: string;
  name: string;
  kind: string;
  is_active: boolean;
  location_id: string;
}

export interface Specialty {
  id: string;
  name: string;
}

export interface Professional {
  id: string;
  display_name: string;
  bio: string;
  user_id: string | null;
  location_id: string;
  photo: ImageRef | null;
  specialty_ids: string[];
  default_commission_pct: string;
  is_active: boolean;
  accepts_online_booking: boolean;
}

export interface OfferedService {
  service_id: string;
  service_name?: string;
  price_override: string | null;
  commission_pct_override: string | null;
  duration_override_min: number | null;
}

// --- Horarios y bloqueos (API del frente A, M4) ------------------------------------------------

/** Franja semanal en hora local del negocio. 0 = lunes ... 6 = domingo. */
export interface WorkingHours {
  weekday: number;
  start_time: string;
  end_time: string;
}

export interface TimeBlock {
  id: string;
  professional_id: string | null;
  resource_id: string | null;
  start_at: string;
  end_at: string;
  reason: string;
  created_at: string;
}

export interface ConflictingAppointment {
  id: string;
  start_at: string;
  end_at: string;
  status: string;
}

// --- Reserva pública (API del frente A, M6) ----------------------------------------------------

export type ImageUrls = Partial<ImageRef["urls"]>;

export interface PublicCompany {
  name: string;
  vertical: Vertical;
  language: Language;
  timezone: string;
  currency: string;
  theme: Partial<Theme>;
  logo: ImageUrls | null;
  address: string;
  city: string;
  phone: string;
  email: string;
  social_links: Partial<Record<SocialNetwork, string>>;
  terms_html: string;
  privacy_html: string;
  cookies_html: string;
  cancel_min_hours: number;
  booking_enabled: boolean;
}

export interface PublicService {
  id: string;
  name: string;
  description: string;
  duration_min: number;
  price: string;
  image: ImageUrls | null;
}

export interface PublicCategory {
  id: string;
  name: string;
  /** R3: solo un servicio de esta categoría por cita. */
  single_choice: boolean;
  services: PublicService[];
}

export interface PublicSpecialty {
  id: string;
  name: string;
}

export interface PublicProfessional {
  id: string;
  display_name: string;
  bio: string;
  photo: ImageUrls | null;
  specialties: PublicSpecialty[];
}

/** Estado de un día en el calendario de reserva (R7). */
export type DayStatus = "available" | "full" | "closed" | "unavailable";

export interface AvailableDays {
  /** Solo los días con horarios. */
  days: string[];
  /** Todos los días del mes con su estado. */
  calendar: { date: string; status: DayStatus }[];
}

export type SlotPeriod = "morning" | "afternoon" | "evening";

export interface Slot {
  start: string;
  end: string;
  period: SlotPeriod;
  professional_ids: string[];
}

export type AppointmentStatus =
  "pending" | "confirmed" | "in_progress" | "completed" | "cancelled" | "no_show" | "rescheduled";

export interface PublicAppointment {
  status: AppointmentStatus;
  start_at: string;
  end_at: string;
  professional: string;
  location: string;
  address: string;
  customer_name: string;
  items: { name: string; duration_min: number; price: string }[];
  price_total: string;
  can_cancel: boolean;
  cancel_deadline: string;
}

export interface PublicBooked extends PublicAppointment {
  manage_url: string;
}

// --- Panel de agenda (M7) ---------------------------------------------------------------------
export interface CustomerRecord {
  id: string;
  full_name: string;
  phone: string;
  email: string;
  birthday: string | null;
  notes: string;
  marketing_consent: boolean;
  data_consent_at: string;
  appointments_count: number;
  created_at: string;
}

export interface Appointment {
  id: string;
  status: AppointmentStatus;
  source: "web" | "dashboard";
  start_at: string;
  end_at: string;
  professional_id: string;
  resource_id: string | null;
  location_id: string;
  customer: Pick<CustomerRecord, "id" | "full_name" | "phone" | "email">;
  items: { service_id: string; price_charged: string; duration_min: number }[];
  price_total: string;
  cancelled_at: string | null;
  cancel_reason: string;
  rescheduled_from_id: string | null;
  created_at: string;
}

export interface IntegrationChannel {
  channel: "whatsapp" | "email";
  sent: number;
  failed: number;
  queued: number;
  last_sent_at: string | null;
}

export interface IntegrationFailure {
  created_at: string;
  kind: "confirmation" | "reminder" | "cancellation" | "reschedule";
  channel: "whatsapp" | "email";
  to: string;
  attempts: number;
  error: string;
}

export interface TenantIntegrations {
  window_days: number;
  whatsapp_enabled: boolean;
  whatsapp_provider: "fake" | "cloud_api" | "other";
  whatsapp_configured: boolean;
  email_backend: string;
  channels: IntegrationChannel[];
  recent_failures: IntegrationFailure[];
}
