import type { TFunction } from "i18next";

export interface TermsSection {
  title: string;
  body: string[];
}

/** Secciones de las condiciones de uso en el idioma activo. Si la traducción no trae una lista
 *  (clave borrada o mal escrita), devuelve una lista vacía en vez de romper la página. */
export function termsSections(t: TFunction): TermsSection[] {
  const sections: unknown = t("platformTerms.sections", { returnObjects: true });
  if (!Array.isArray(sections)) return [];
  return sections.filter(
    (section): section is TermsSection =>
      typeof section === "object" &&
      section !== null &&
      typeof (section as TermsSection).title === "string" &&
      Array.isArray((section as TermsSection).body),
  );
}
