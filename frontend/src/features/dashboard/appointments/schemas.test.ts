import { describe, expect, it } from "vitest";
import { appointmentPayload, appointmentSchema, type AppointmentValues } from "./schemas";

const values: AppointmentValues = {
  service_ids: ["s1", "s2"],
  professional_id: "",
  date: "2026-11-09",
  start_at: "2026-11-09T10:00",
  customer_mode: "existing",
  customer_id: "c1",
  full_name: " Ana ",
  phone: " +573001234567 ",
  email: "",
  marketing_consent: false,
};
describe("appointment payload", () => {
  it("sends exactly the existing customer reference and preserves local datetime", () => {
    expect(appointmentPayload(values)).toEqual({
      service_ids: ["s1", "s2"],
      professional_id: null,
      start_at: "2026-11-09T10:00",
      customer_id: "c1",
    });
  });
  it("sends exactly the nested new customer and trims contact fields", () => {
    const payload = appointmentPayload({ ...values, professional_id: "p1", customer_mode: "new" });
    expect(payload).toEqual({
      service_ids: ["s1", "s2"],
      professional_id: "p1",
      start_at: values.start_at,
      customer: { full_name: "Ana", phone: "+573001234567", email: "", marketing_consent: false },
    });
    expect(payload).not.toHaveProperty("customer_id");
  });
  it("requires a slot, services and an identified customer", () => {
    expect(appointmentSchema.safeParse(values).success).toBe(true);
    for (const input of [
      { ...values, service_ids: [] },
      { ...values, start_at: "" },
      { ...values, customer_id: "" },
      { ...values, customer_mode: "new", phone: "x" },
    ])
      expect(appointmentSchema.safeParse(input).success).toBe(false);
  });
});
