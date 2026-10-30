import { z } from "zod";
import { isHexColor } from "./contrast";

const SLUG = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/;
const RESERVED_SLUGS = [
  "admin",
  "api",
  "www",
  "app",
  "mail",
  "static",
  "media",
  "support",
  "status",
];
const HOST = /^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/;

// Los mensajes son claves de i18n: la pantalla las traduce.
export const tenantCreateSchema = z.object({
  name: z.string().trim().min(1, "required").max(150),
  slug: z
    .string()
    .trim()
    .toLowerCase()
    .regex(SLUG, "slugFormat")
    .refine((slug) => !RESERVED_SLUGS.includes(slug), "slugReserved"),
  plan_id: z.string().min(1, "required"),
  vertical: z.enum(["barbershop", "salon", "nails", "spa"]),
  timezone: z.string().trim().min(1, "required"),
  currency: z.string().trim().length(3, "currencyFormat"),
  language: z.enum(["es", "en"]),
  owner_name: z.string().trim().min(1, "required").max(150),
  owner_email: z.email("emailFormat"),
});
export type TenantCreateValues = z.infer<typeof tenantCreateSchema>;

export const tenantEditSchema = tenantCreateSchema.pick({
  name: true,
  plan_id: true,
  vertical: true,
  timezone: true,
  currency: true,
  language: true,
});
export type TenantEditValues = z.infer<typeof tenantEditSchema>;

export const themeSchema = z.object({
  primary: z.string().refine(isHexColor, "hexFormat"),
  secondary: z.string().refine(isHexColor, "hexFormat"),
  background: z.string().refine(isHexColor, "hexFormat"),
  surface: z.string().refine(isHexColor, "hexFormat"),
  text: z.string().refine(isHexColor, "hexFormat"),
});
export type ThemeValues = z.infer<typeof themeSchema>;

export const domainSchema = z.object({
  host: z.string().trim().toLowerCase().regex(HOST, "hostFormat"),
});
export type DomainValues = z.infer<typeof domainSchema>;

export const planSchema = z.object({
  name: z.string().trim().min(1, "required").max(100),
  modules: z.array(z.enum(["booking", "commissions", "reports", "notifications_whatsapp"])),
  max_professionals: z.number().int().min(1, "min1"),
  max_locations: z.number().int().min(1, "min1"),
  apply_to_tenants: z.boolean(),
});
export type PlanValues = z.infer<typeof planSchema>;

export const loginSchema = z.object({
  email: z.email("emailFormat"),
  password: z.string().min(1, "required"),
  totp_code: z.string(),
});
export type LoginValues = z.infer<typeof loginSchema>;

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "required"),
    new_password: z.string().min(10, "passwordMin"),
    repeat_password: z.string(),
  })
  .refine((v) => v.new_password === v.repeat_password, {
    path: ["repeat_password"],
    message: "passwordsMismatch",
  });
export type ChangePasswordValues = z.infer<typeof changePasswordSchema>;

export const resetPasswordSchema = z
  .object({
    new_password: z.string().min(10, "passwordMin"),
    repeat_password: z.string(),
  })
  .refine((v) => v.new_password === v.repeat_password, {
    path: ["repeat_password"],
    message: "passwordsMismatch",
  });
export type ResetPasswordValues = z.infer<typeof resetPasswordSchema>;

export const forgotSchema = z.object({ email: z.email("emailFormat") });
export type ForgotValues = z.infer<typeof forgotSchema>;
