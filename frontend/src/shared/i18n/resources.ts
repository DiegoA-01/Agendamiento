/** Traducciones repartidas en un archivo por funcionalidad: `locales/<idioma>/<area>.json`.
 *
 * Cada área es dueña de sus claves de primer nivel, así dos personas pueden agregar textos sin
 * tocar el mismo archivo. Un archivo nuevo se carga solo: no hay que registrarlo en ningún lado.
 * Todas se unen en un único espacio `translation`, por eso las claves siguen siendo `t("area.x")`.
 */

export type Dictionary = Record<string, unknown>;
/** Ruta del archivo (`./locales/es/auth.json`) → contenido. */
export type LocaleFiles = Record<string, Dictionary>;

const FILE_RE = /\/locales\/([a-z]{2})\/([\w-]+)\.json$/;

export function parseLocalePath(path: string): { lang: string; area: string } {
  const match = FILE_RE.exec(path);
  if (!match) throw new Error(`Ruta de traducción inválida: ${path}`);
  return { lang: match[1], area: match[2] };
}

/** Une los archivos de cada idioma. Falla si dos archivos usan la misma clave de primer nivel. */
export function mergeLocaleFiles(files: LocaleFiles): Record<string, Dictionary> {
  const byLang: Record<string, Dictionary> = {};
  const owner: Record<string, string> = {};
  for (const [path, content] of Object.entries(files)) {
    const { lang } = parseLocalePath(path);
    const merged = (byLang[lang] ??= {});
    for (const [key, value] of Object.entries(content)) {
      const id = `${lang}:${key}`;
      if (id in owner) {
        throw new Error(`La clave "${key}" (${lang}) está en ${owner[id]} y en ${path}`);
      }
      owner[id] = path;
      merged[key] = value;
    }
  }
  return byLang;
}

export const localeFiles: LocaleFiles = import.meta.glob<Dictionary>("./locales/*/*.json", {
  eager: true,
  import: "default",
});

export const translations = mergeLocaleFiles(localeFiles);
