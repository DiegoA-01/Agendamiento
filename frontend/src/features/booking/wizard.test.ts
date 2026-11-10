import { describe, expect, it } from "vitest";
import type { PublicCategory, Slot } from "../../shared/api/types";
import {
  addMonths,
  bookingPayload,
  calendarCells,
  dayStatuses,
  formatTime,
  looksLikePhone,
  selectedServices,
  slotsByPeriod,
  todayIn,
  toggleService,
  totals,
} from "./wizard";

const CATEGORIES: PublicCategory[] = [
  {
    id: "c1",
    name: "Cortes",
    single_choice: false,
    services: [
      {
        id: "corte",
        name: "Corte",
        description: "",
        duration_min: 30,
        price: "30000.10",
        image: null,
      },
      {
        id: "diseno",
        name: "Diseño",
        description: "",
        duration_min: 45,
        price: "40000.20",
        image: null,
      },
    ],
  },
  {
    id: "c2",
    name: "Barba",
    single_choice: false,
    services: [
      { id: "barba", name: "Barba", description: "", duration_min: 20, price: "0.10", image: null },
    ],
  },
];

describe("servicios elegidos", () => {
  it("siguen el orden del catálogo, no el de los clics, y suman bien los centavos", () => {
    const services = selectedServices(CATEGORIES, ["barba", "corte"]);
    expect(services.map((s) => s.id)).toEqual(["corte", "barba"]);
    expect(totals(services)).toEqual({ minutes: 50, price: "30000.20" });
  });
});

describe("calendario", () => {
  it("noviembre de 2026 empieza en domingo: 6 huecos antes del día 1", () => {
    const cells = calendarCells("2026-11");
    expect(cells.slice(0, 7)).toEqual([null, null, null, null, null, null, "2026-11-01"]);
    expect(cells.at(-1)).toBe("2026-11-30");
    expect(cells.filter(Boolean)).toHaveLength(30);
  });

  it("febrero bisiesto y meses que cruzan el año", () => {
    expect(calendarCells("2028-02").filter(Boolean)).toHaveLength(29);
    expect(addMonths("2026-12", 1)).toBe("2027-01");
    expect(addMonths("2026-01", -1)).toBe("2025-12");
  });

  it("hoy se calcula en la zona del negocio", () => {
    // 3:00 UTC del 6 de noviembre todavía es 5 de noviembre en Bogotá.
    const now = new Date("2026-11-06T03:00:00Z");
    expect(todayIn("America/Bogota", now)).toBe("2026-11-05");
    expect(todayIn("UTC", now)).toBe("2026-11-06");
  });
});

describe("horarios", () => {
  it("se agrupan por mañana, tarde y noche", () => {
    const slot = (start: string, period: Slot["period"]): Slot => ({
      start,
      end: start,
      period,
      professional_ids: [],
    });
    const groups = slotsByPeriod([
      slot("2026-11-09T09:00:00-05:00", "morning"),
      slot("2026-11-09T14:00:00-05:00", "afternoon"),
      slot("2026-11-09T18:30:00-05:00", "evening"),
      slot("2026-11-09T10:00:00-05:00", "morning"),
    ]);
    expect(groups.morning).toHaveLength(2);
    expect(groups.afternoon).toHaveLength(1);
    expect(groups.evening).toHaveLength(1);
  });

  it("la hora se muestra en la zona del negocio", () => {
    expect(formatTime("2026-11-09T14:00:00Z", "es-CO", "America/Bogota")).toMatch(/9:00/);
  });
});

describe("datos y envío", () => {
  it.each([
    ["300 123 4567", true],
    ["(300) 123-4567", true],
    ["+57 300 1234567", true],
    ["123", false],
    ["llámame", false],
  ])("celular %s parece válido: %s", (phone, valid) => {
    expect(looksLikePhone(phone)).toBe(valid);
  });

  it("arma el cuerpo de la reserva con el honeypot y sin espacios de más", () => {
    expect(
      bookingPayload({
        serviceIds: ["corte"],
        professionalId: null,
        start: "2026-11-09T10:00:00-05:00",
        customer: { full_name: " Laura ", phone: " 3001112233 ", email: "" },
        acceptDataPolicy: true,
        marketingConsent: false,
        website: "",
      }),
    ).toEqual({
      service_ids: ["corte"],
      professional_id: null,
      start_at: "2026-11-09T10:00:00-05:00",
      customer: { full_name: "Laura", phone: "3001112233", email: "" },
      accept_data_policy: true,
      marketing_consent: false,
      website: "",
    });
  });
});

describe("dayStatuses", () => {
  it("usa el estado de cada día que manda la API", () => {
    const statuses = dayStatuses({
      days: ["2026-11-02"],
      calendar: [
        { date: "2026-11-01", status: "closed" },
        { date: "2026-11-02", status: "available" },
        { date: "2026-11-03", status: "full" },
      ],
    });
    expect(statuses.get("2026-11-01")).toBe("closed");
    expect(statuses.get("2026-11-02")).toBe("available");
    expect(statuses.get("2026-11-03")).toBe("full");
    expect(statuses.get("2026-11-04")).toBeUndefined();
  });

  it("sin calendario, los días de `days` quedan disponibles", () => {
    const statuses = dayStatuses({ days: ["2026-11-02"] } as never);
    expect([...statuses]).toEqual([["2026-11-02", "available"]]);
  });

  it("sin datos no hay estados", () => {
    expect(dayStatuses(undefined).size).toBe(0);
  });
});

describe("toggleService (R3)", () => {
  const svc = (id: string) => ({
    id,
    name: id,
    description: "",
    duration_min: 30,
    price: "10000.00",
    image: null,
  });
  const categories = [
    { id: "cortes", name: "Cortes", single_choice: true, services: [svc("corte"), svc("fade")] },
    { id: "extras", name: "Extras", single_choice: false, services: [svc("barba"), svc("cejas")] },
  ];

  it("un segundo corte reemplaza al primero", () => {
    expect(toggleService(categories, ["corte"], "fade")).toEqual(["fade"]);
  });

  it("corte más barba y cejas se suman", () => {
    expect(toggleService(categories, ["corte", "barba"], "cejas")).toEqual([
      "corte",
      "barba",
      "cejas",
    ]);
  });

  it("al reemplazar conserva los demás servicios", () => {
    expect(toggleService(categories, ["corte", "barba"], "fade")).toEqual(["barba", "fade"]);
  });

  it("tocar uno elegido lo quita", () => {
    expect(toggleService(categories, ["corte", "barba"], "corte")).toEqual(["barba"]);
  });
});
