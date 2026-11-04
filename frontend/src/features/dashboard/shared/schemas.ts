import { z } from "zod";
import {
  SOCIAL_NETWORKS,
  type Company,
  type OfferedService,
  type Professional,
  type Service,
} from "../../../shared/api/types";

// Los mensajes son claves de i18n (`errors.*` o `common.*`): la pantalla las traduce.
const MONEY = /^\d{1,10}(\.\d{1,2})?$/;
const PERCENT = /^\d{1,3}(\.\d{1,2})?$/;

const money = z.string().trim().regex(MONEY, "moneyFormat");
const percent = z
  .string()
  .trim()
  .regex(PERCENT, "percentFormat")
  .refine((value) => Number(value) <= 100, "percentFormat");
const optionalUrl = z.union([z.literal(""), z.url("urlFormat")]);

/** Texto vacío → null (el override "no aplica"); si no, el valor tal cual. */
function blankToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

// --- Empresa ------------------------------------------------------------------------------------

export const companySchema = z.object({
  trade_name: z.string().trim().min(1, "required").max(200),
  legal_name: z.string().trim().max(200),
  tax_id: z.string().trim().max(30),
  address: z.string().trim().max(250),
  city: z.string().trim().max(100),
  phone: z.string().trim().max(30),
  email: z.union([z.literal(""), z.email("emailFormat")]),
  social: z.object(
    Object.fromEntries(SOCIAL_NETWORKS.map((key) => [key, optionalUrl])) as Record<
      (typeof SOCIAL_NETWORKS)[number],
      typeof optionalUrl
    >,
  ),
  terms_html: z.string(),
  privacy_html: z.string(),
  cookies_html: z.string(),
});
export type CompanyValues = z.infer<typeof companySchema>;

export function companyToValues(company: Company): CompanyValues {
  return {
    trade_name: company.trade_name,
    legal_name: company.legal_name,
    tax_id: company.tax_id,
    address: company.address,
    city: company.city,
    phone: company.phone,
    email: company.email,
    social: Object.fromEntries(
      SOCIAL_NETWORKS.map((key) => [key, company.social_links[key] ?? ""]),
    ) as CompanyValues["social"],
    terms_html: company.terms_html,
    privacy_html: company.privacy_html,
    cookies_html: company.cookies_html,
  };
}

/** Las redes vacías no se envían: el servidor solo acepta URLs. */
export function companyPayload(values: CompanyValues) {
  const { social, ...rest } = values;
  const social_links = Object.fromEntries(
    Object.entries(social).filter(([, url]) => url.trim() !== ""),
  );
  return { ...rest, social_links };
}

// --- Catálogo -----------------------------------------------------------------------------------

export const categorySchema = z.object({
  name: z.string().trim().min(1, "required").max(100),
});
export type CategoryValues = z.infer<typeof categorySchema>;

export const serviceSchema = z.object({
  category_id: z.string().min(1, "required"),
  name: z.string().trim().min(1, "required").max(150),
  description: z.string().trim(),
  duration_min: z.number("required").int().min(5, "durationRange").max(1440, "durationRange"),
  buffer_min: z.number("required").int().min(0, "bufferRange").max(240, "bufferRange"),
  price: money,
  is_active: z.boolean(),
  requires_resource: z.boolean(),
});
export type ServiceValues = z.infer<typeof serviceSchema>;

export function serviceToValues(service: Service | undefined, categoryId = ""): ServiceValues {
  return {
    category_id: service?.category_id ?? categoryId,
    name: service?.name ?? "",
    description: service?.description ?? "",
    duration_min: service?.duration_min ?? 30,
    buffer_min: service?.buffer_min ?? 0,
    price: service?.price ?? "",
    is_active: service?.is_active ?? true,
    requires_resource: service?.requires_resource ?? false,
  };
}

export const resourceSchema = z.object({
  name: z.string().trim().min(1, "required").max(100),
  kind: z.string().trim().max(50),
  is_active: z.boolean(),
});
export type ResourceValues = z.infer<typeof resourceSchema>;

// --- Equipo -------------------------------------------------------------------------------------

export const professionalSchema = z.object({
  display_name: z.string().trim().min(1, "required").max(150),
  bio: z.string().trim(),
  default_commission_pct: percent,
  specialty_ids: z.array(z.string()),
  is_active: z.boolean(),
  accepts_online_booking: z.boolean(),
});
export type ProfessionalValues = z.infer<typeof professionalSchema>;

export function professionalToValues(professional: Professional | undefined): ProfessionalValues {
  return {
    display_name: professional?.display_name ?? "",
    bio: professional?.bio ?? "",
    default_commission_pct: professional?.default_commission_pct ?? "0",
    specialty_ids: professional?.specialty_ids ?? [],
    is_active: professional?.is_active ?? true,
    accepts_online_booking: professional?.accepts_online_booking ?? true,
  };
}

/** Una fila del editor de servicios del profesional: los overrides vacíos usan el valor base. */
export const offerRowSchema = z.object({
  service_id: z.string(),
  offered: z.boolean(),
  price_override: z.union([z.literal(""), money]),
  duration_override_min: z.union([
    z.literal(""),
    z
      .string()
      .regex(/^\d{1,4}$/, "durationRange")
      .refine((v) => {
        const minutes = Number(v);
        return minutes >= 5 && minutes <= 1440;
      }, "durationRange"),
  ]),
  commission_pct_override: z.union([z.literal(""), percent]),
});
export const offersSchema = z.object({ rows: z.array(offerRowSchema) });
export type OffersValues = z.infer<typeof offersSchema>;

export function offersToValues(services: Service[], offers: OfferedService[]): OffersValues {
  const byService = new Map(offers.map((offer) => [offer.service_id, offer]));
  return {
    rows: services.map((service) => {
      const offer = byService.get(service.id);
      return {
        service_id: service.id,
        offered: Boolean(offer),
        price_override: offer?.price_override ?? "",
        duration_override_min:
          offer?.duration_override_min != null ? String(offer.duration_override_min) : "",
        commission_pct_override: offer?.commission_pct_override ?? "",
      };
    }),
  };
}

/** Lo que espera `PUT professionals/{id}/services/`: solo los servicios marcados. */
export function offersPayload(values: OffersValues): { services: OfferedService[] } {
  return {
    services: values.rows
      .filter((row) => row.offered)
      .map((row) => {
        const duration = blankToNull(row.duration_override_min);
        return {
          service_id: row.service_id,
          price_override: blankToNull(row.price_override),
          duration_override_min: duration === null ? null : Number(duration),
          commission_pct_override: blankToNull(row.commission_pct_override),
        };
      }),
  };
}
