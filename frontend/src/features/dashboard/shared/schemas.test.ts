import { describe, expect, it } from "vitest";
import type { Company, OfferedService, Service } from "../../../shared/api/types";
import { formatMoney } from "../../../shared/money";
import {
  companyPayload,
  companySchema,
  companyToValues,
  offersPayload,
  offersSchema,
  offersToValues,
  professionalSchema,
  professionalToValues,
  serviceSchema,
  serviceToValues,
} from "./schemas";
import { can } from "./useCan";

const COMPANY: Company = {
  legal_name: "",
  trade_name: "El Filo",
  tax_id: "",
  address: "",
  city: "",
  phone: "",
  email: "",
  logo: null,
  terms_html: "",
  privacy_html: "",
  cookies_html: "",
  social_links: { instagram: "https://instagram.com/elfilo" },
};

function service(id: string, overrides: Partial<Service> = {}): Service {
  return {
    id,
    category_id: "c1",
    name: id,
    description: "",
    duration_min: 30,
    buffer_min: 0,
    price: "30000.00",
    is_active: true,
    requires_resource: false,
    image: null,
    ...overrides,
  };
}

describe("empresa", () => {
  it("solo envía las redes que tienen dirección", () => {
    const values = companyToValues(COMPANY);
    expect(values.social.facebook).toBe("");
    expect(companyPayload(values).social_links).toEqual({
      instagram: "https://instagram.com/elfilo",
    });
  });

  it("rechaza redes que no son direcciones y exige el nombre comercial", () => {
    const values = companyToValues({ ...COMPANY, trade_name: " " });
    values.social.tiktok = "tiktok.com/sin-protocolo";
    const result = companySchema.safeParse(values);
    expect(result.success).toBe(false);
    const paths = result.error?.issues.map((issue) => issue.path.join("."));
    expect(paths).toEqual(expect.arrayContaining(["trade_name", "social.tiktok"]));
  });
});

describe("servicios", () => {
  it.each([
    ["30000", true],
    ["30000.5", true],
    ["30000.55", true],
    ["30000.555", false],
    ["-1", false],
    ["1e5", false],
    ["", false],
  ])("precio %s válido: %s", (price, valid) => {
    const values = { ...serviceToValues(undefined, "c1"), name: "Corte", price };
    expect(serviceSchema.safeParse(values).success).toBe(valid);
  });

  it("la duración va de 5 a 1440 minutos", () => {
    const base = { ...serviceToValues(undefined, "c1"), name: "Corte", price: "1000" };
    expect(serviceSchema.safeParse({ ...base, duration_min: 4 }).success).toBe(false);
    expect(serviceSchema.safeParse({ ...base, duration_min: 1441 }).success).toBe(false);
    expect(serviceSchema.safeParse({ ...base, duration_min: 45 }).success).toBe(true);
  });
});

describe("equipo", () => {
  it.each([
    ["0", true],
    ["40", true],
    ["45.5", true],
    ["100", true],
    ["100.01", false],
    ["-5", false],
    ["40.123", false],
  ])("comisión %s válida: %s", (pct, valid) => {
    const values = { ...professionalToValues(undefined), display_name: "Ana" };
    expect(professionalSchema.safeParse({ ...values, default_commission_pct: pct }).success).toBe(
      valid,
    );
  });
});

describe("servicios del profesional", () => {
  const services = [service("corte"), service("barba"), service("cejas")];
  const offers: OfferedService[] = [
    {
      service_id: "corte",
      price_override: "35000.00",
      commission_pct_override: null,
      duration_override_min: 40,
    },
  ];

  it("una fila por servicio, marcada si ya lo ofrece", () => {
    const values = offersToValues(services, offers);
    expect(values.rows.map((row) => [row.service_id, row.offered])).toEqual([
      ["corte", true],
      ["barba", false],
      ["cejas", false],
    ]);
    expect(values.rows[0]).toMatchObject({
      price_override: "35000.00",
      duration_override_min: "40",
    });
  });

  it("envía solo los marcados y los overrides vacíos como null", () => {
    const values = offersToValues(services, offers);
    values.rows[1] = { ...values.rows[1], offered: true, commission_pct_override: "50" };
    values.rows[0] = { ...values.rows[0], price_override: " " };

    expect(offersPayload(values)).toEqual({
      services: [
        {
          service_id: "corte",
          price_override: null,
          duration_override_min: 40,
          commission_pct_override: null,
        },
        {
          service_id: "barba",
          price_override: null,
          duration_override_min: null,
          commission_pct_override: "50",
        },
      ],
    });
  });

  it("valida los overrides", () => {
    const values = offersToValues(services, []);
    values.rows[0] = { ...values.rows[0], offered: true, duration_override_min: "2" };
    values.rows[1] = { ...values.rows[1], offered: true, commission_pct_override: "150" };
    const result = offersSchema.safeParse(values);
    expect(result.success).toBe(false);
    expect(result.error?.issues.map((issue) => issue.path.join("."))).toEqual([
      "rows.0.duration_override_min",
      "rows.1.commission_pct_override",
    ]);
  });
});

describe("utilidades", () => {
  it("formatea montos en la moneda del negocio sin decimales si no hacen falta", () => {
    expect(formatMoney("30000.00", "COP", "es-CO").replace(/\s/g, " ")).toMatch(/30\.000/);
    expect(formatMoney("12.50", "USD", "en-US")).toBe("$12.50");
    expect(formatMoney("no-es-numero", "COP", "es")).toBe("no-es-numero");
  });

  it("can() lee los permisos de /me/", () => {
    const me = { permissions: { company: { scope: "all" as const, actions: ["view"] } } };
    expect(can(me, "company", "view")).toBe(true);
    expect(can(me, "company", "update")).toBe(false);
    expect(can(undefined, "company", "view")).toBe(false);
  });
});
