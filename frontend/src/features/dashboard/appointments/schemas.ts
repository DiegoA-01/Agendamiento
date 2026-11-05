import { z } from "zod";
import { looksLikePhone } from "../../booking/wizard";

const name = z.string().trim().min(1, "required");
const phone = z.string().trim().refine(looksLikePhone, "phoneFormat");
const email = z.union([z.literal(""), z.email("emailFormat")]);
export const customerSchema = z.object({
  full_name: name,
  phone,
  email,
  birthday: z.string(),
  notes: z.string(),
  marketing_consent: z.boolean(),
  data_consent: z.boolean(),
});
export type CustomerValues = z.infer<typeof customerSchema>;
export const appointmentSchema = z
  .object({
    service_ids: z.array(z.string()).min(1, "required"),
    professional_id: z.string(),
    date: name,
    start_at: name,
    customer_mode: z.enum(["existing", "new"]),
    customer_id: z.string(),
    full_name: z.string(),
    phone: z.string(),
    email: z.string(),
    marketing_consent: z.boolean(),
  })
  .superRefine((value, ctx) => {
    if (value.customer_mode === "existing" && !value.customer_id)
      ctx.addIssue({ code: "custom", path: ["customer_id"], message: "required" });
    if (value.customer_mode === "new") {
      if (!email.safeParse(value.email).success)
        ctx.addIssue({ code: "custom", path: ["email"], message: "emailFormat" });
      if (!value.full_name.trim())
        ctx.addIssue({ code: "custom", path: ["full_name"], message: "required" });
      if (!looksLikePhone(value.phone))
        ctx.addIssue({ code: "custom", path: ["phone"], message: "phoneFormat" });
    }
  });
export type AppointmentValues = z.infer<typeof appointmentSchema>;
export function appointmentPayload(values: AppointmentValues) {
  const base = {
    service_ids: values.service_ids,
    professional_id: values.professional_id || null,
    start_at: values.start_at,
  };
  return values.customer_mode === "existing"
    ? { ...base, customer_id: values.customer_id }
    : {
        ...base,
        customer: {
          full_name: values.full_name.trim(),
          phone: values.phone.trim(),
          email: values.email.trim(),
          marketing_consent: values.marketing_consent,
        },
      };
}
