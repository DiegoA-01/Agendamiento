import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import i18n from "../../shared/i18n";
import { PUBLIC_PAGES, publicRoutes } from "./routes";

function render(url: string): string {
  return renderToString(
    createElement(
      I18nextProvider,
      { i18n },
      createElement(
        MemoryRouter,
        { initialEntries: [url] },
        createElement(Routes, null, publicRoutes()),
      ),
    ),
  );
}

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

  it.each([
    ["/reservar", "Reservar una cita"],
    ["/cita/abc123", "Tu cita"],
    ["/terminos", "Términos y condiciones"],
    ["/privacidad", "Política de privacidad"],
    ["/cookies", "Política de cookies"],
  ])("%s muestra su título traducido", (url, title) => {
    const html = render(url);
    expect(html).toContain(title);
    expect(html).toContain("M6");
  });
});
