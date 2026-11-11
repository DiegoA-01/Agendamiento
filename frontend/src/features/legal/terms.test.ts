import type { TFunction } from "i18next";
import { describe, expect, it } from "vitest";
import i18n from "../../shared/i18n";
import { termsSections } from "./terms";

describe("condiciones de uso de la plataforma (S8)", () => {
  it("trae las mismas secciones en español e inglés, todas con texto", async () => {
    const es = termsSections(i18n.getFixedT("es"));
    const en = termsSections(i18n.getFixedT("en"));
    expect(es.length).toBeGreaterThanOrEqual(10);
    expect(en).toHaveLength(es.length);
    for (const [index, section] of es.entries()) {
      expect(section.title).not.toBe("");
      expect(section.body.length).toBeGreaterThan(0);
      expect(en[index].body).toHaveLength(section.body.length);
    }
    await i18n.changeLanguage("es");
  });

  it("no rompe la página si la traducción no es una lista", () => {
    const broken = (() => "platformTerms.sections") as unknown as TFunction;
    expect(termsSections(broken)).toEqual([]);
  });
});
