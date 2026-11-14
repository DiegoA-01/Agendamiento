import { describe, expect, it } from "vitest";
import { fillMonths, lastMonths, percentChange } from "./months";

describe("meses del Inicio", () => {
  it("cuenta los últimos meses cruzando el año", () => {
    expect(lastMonths("2026-11-13", 6)).toEqual([
      "2026-06",
      "2026-07",
      "2026-08",
      "2026-09",
      "2026-10",
      "2026-11",
    ]);
    expect(lastMonths("2027-02-01", 4)).toEqual(["2026-11", "2026-12", "2027-01", "2027-02"]);
  });

  it("llena con cero los meses sin ventas", () => {
    expect(
      fillMonths(["2026-10", "2026-11"], [{ key: "2026-11-01 00:00:00-05:00", sales: "80000.00" }]),
    ).toEqual([
      { month: "2026-10", sales: 0 },
      { month: "2026-11", sales: 80000 },
    ]);
  });

  it("calcula el cambio frente al mes anterior y no divide por cero", () => {
    expect(percentChange(110, 100)).toBe(10);
    expect(percentChange(82, 100)).toBe(-18);
    expect(percentChange(50, 0)).toBeNull();
  });
});
