import { describe, expect, it } from "vitest";
import { exportUrl, reportParams } from "./api";
import { isValidRange, lastSevenDays, monthRange, previousMonthRange, todayIn } from "./range";

describe("rangos de los reportes", () => {
  it("el mes en curso va del 1 al último día, con bisiestos", () => {
    expect(monthRange("2026-11-09")).toEqual({ from: "2026-11-01", to: "2026-11-30" });
    expect(monthRange("2028-02-10")).toEqual({ from: "2028-02-01", to: "2028-02-29" });
    expect(monthRange("2026-12-31")).toEqual({ from: "2026-12-01", to: "2026-12-31" });
  });

  it("el mes anterior cruza el año", () => {
    expect(previousMonthRange("2026-01-15")).toEqual({ from: "2025-12-01", to: "2025-12-31" });
    expect(previousMonthRange("2026-03-01")).toEqual({ from: "2026-02-01", to: "2026-02-28" });
  });

  it("los últimos 7 días incluyen hoy", () => {
    expect(lastSevenDays("2026-03-03")).toEqual({ from: "2026-02-25", to: "2026-03-03" });
  });

  it("hoy se calcula en la zona del negocio", () => {
    // 2 de marzo 03:00 UTC sigue siendo 1 de marzo en Bogotá.
    expect(todayIn("America/Bogota", new Date("2026-03-02T03:00:00Z"))).toBe("2026-03-01");
  });

  it("valida el orden y el máximo de un año", () => {
    expect(isValidRange({ from: "2026-03-01", to: "2026-03-31" })).toBe(true);
    expect(isValidRange({ from: "2026-03-31", to: "2026-03-01" })).toBe(false);
    expect(isValidRange({ from: "2025-01-01", to: "2026-03-01" })).toBe(false);
    expect(isValidRange({ from: "", to: "2026-03-01" })).toBe(false);
  });
});

describe("parámetros", () => {
  it("arma la consulta y el enlace del CSV", () => {
    const filters = { from: "2026-03-01", to: "2026-03-31", professional_id: "p1" };
    expect(reportParams(filters, { group_by: "week" }).toString()).toBe(
      "from=2026-03-01&to=2026-03-31&group_by=week&professional_id=p1",
    );
    expect(exportUrl("reports/sales/", { from: "2026-03-01", to: "2026-03-31" })).toBe(
      "/api/v1/reports/sales/export/?from=2026-03-01&to=2026-03-31",
    );
  });
});
