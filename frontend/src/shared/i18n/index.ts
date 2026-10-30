import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import { translations } from "./resources";

export const SUPPORTED_LANGUAGES = ["es", "en"] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];
export const DEFAULT_LANGUAGE: Language = "es";
const STORAGE_KEY = "lang";

function initialLanguage(): Language {
  try {
    const stored = globalThis.localStorage?.getItem(STORAGE_KEY);
    if (stored && (SUPPORTED_LANGUAGES as readonly string[]).includes(stored)) {
      return stored as Language;
    }
  } catch {
    // localStorage no disponible: usamos el idioma por defecto.
  }
  return DEFAULT_LANGUAGE;
}

export function setLanguage(lang: Language) {
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, lang);
  } catch {
    // ignorar
  }
  return i18n.changeLanguage(lang);
}

void i18n.use(initReactI18next).init({
  resources: {
    es: { translation: translations.es },
    en: { translation: translations.en },
  },
  lng: initialLanguage(),
  fallbackLng: DEFAULT_LANGUAGE,
  interpolation: { escapeValue: false },
});

export default i18n;
