import { describe, expect, it } from "vitest";
import type { PublicCategory } from "../../shared/api/types";
import { DEMO_STEPS, demoServices, nextDays, nextDemoStep } from "./howItWorks";

const service = (id: string) => ({
  id,
  name: id,
  description: "",
  duration_min: 30,
  price: "20000.00",
  image: null,
});

describe("celular de la portada", () => {
  it("recorre los tres pasos, la confirmación y vuelve a empezar", () => {
    expect(DEMO_STEPS).toEqual(["services", "schedule", "details", "done"]);
    expect([0, 1, 2, 3].map(nextDemoStep)).toEqual([1, 2, 3, 0]);
  });

  it("muestra los primeros servicios del negocio, sin importar la categoría", () => {
    const categories: PublicCategory[] = [
      { id: "c1", name: "Cortes", single_choice: true, services: [service("a"), service("b")] },
      { id: "c2", name: "Barba", single_choice: true, services: [service("c"), service("d")] },
    ];
    expect(demoServices(categories).map((s) => s.id)).toEqual(["a", "b", "c"]);
    expect(demoServices(undefined)).toEqual([]);
  });

  it("arma los próximos días cruzando el fin de mes", () => {
    expect(nextDays("2026-11-29", 4)).toEqual([
      "2026-11-29",
      "2026-11-30",
      "2026-12-01",
      "2026-12-02",
    ]);
  });
});
