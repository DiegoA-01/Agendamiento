import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { I18nextProvider } from "react-i18next";
import { describe, expect, it } from "vitest";
import { LanguageSwitcher } from "../ui/LanguageSwitcher";
import i18n, { DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES } from "./index";
import { localeFiles, mergeLocaleFiles, parseLocalePath, translations } from "./resources";

const { es, en } = translations;

function areas(lang: string): string[] {
  return Object.keys(localeFiles)
    .map(parseLocalePath)
    .filter((file) => file.lang === lang)
    .map((file) => file.area)
    .sort();
}

function keys(obj: Record<string, unknown>, prefix = ""): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    typeof v === "object" && v !== null
      ? keys(v as Record<string, unknown>, `${prefix}${k}.`)
      : [`${prefix}${k}`],
  );
}

describe("i18n", () => {
  it("usa español por defecto y soporta es/en", () => {
    expect(DEFAULT_LANGUAGE).toBe("es");
    expect(SUPPORTED_LANGUAGES).toEqual(["es", "en"]);
    expect(i18n.language).toBe("es");
  });

  it("es y en tienen exactamente las mismas claves", () => {
    expect(keys(en).sort()).toEqual(keys(es).sort());
  });

  it("es y en tienen los mismos archivos por área", () => {
    expect(areas("en")).toEqual(areas("es"));
    expect(areas("es")).toContain("common");
  });

  it("rechaza dos archivos que usan la misma clave de primer nivel", () => {
    expect(() =>
      mergeLocaleFiles({
        "./locales/es/a.json": { nav: {} },
        "./locales/es/b.json": { nav: {} },
      }),
    ).toThrow(/nav/);
  });

  it("traduce y cambia de idioma", async () => {
    await i18n.changeLanguage("en");
    expect(i18n.t("home.tagline")).toBe("Book your appointment in under a minute.");
    await i18n.changeLanguage("es");
    expect(i18n.t("home.tagline")).toBe("Reserva tu cita en menos de un minuto.");
  });

  it("renderiza el selector de idioma", () => {
    const html = renderToString(
      createElement(I18nextProvider, { i18n }, createElement(LanguageSwitcher)),
    );
    expect(html).toContain("Idioma");
    expect(html).toContain("English");
  });
});
