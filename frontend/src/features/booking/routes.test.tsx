import { describe, expect, it } from "vitest";
import { PUBLIC_PAGES } from "./routes";

describe("rutas públicas del negocio (spec §13)", () => {
  it("incluye las cinco rutas de la spec", () => {
    expect(PUBLIC_PAGES.map((page) => page.path)).toEqual([
      "/reservar",
      "/cita/:token",
      "/terminos",
      "/privacidad",
      "/cookies",
    ]);
  });
});
