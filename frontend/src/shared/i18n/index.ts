import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import { translations } from "./resources";

export const SUPPORTED_LANGUAGES = ["es", "en"] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];
export const DEFAULT_LANGUAGE: Language = "es";
// No hay selector de idioma: se arranca en español y cada sitio o panel cambia al idioma
// configurado del negocio (PublicLayout y DashboardLayout).

void i18n.use(initReactI18next).init({
  resources: {
    es: { translation: translations.es },
    en: { translation: translations.en },
  },
  lng: DEFAULT_LANGUAGE,
  fallbackLng: DEFAULT_LANGUAGE,
  interpolation: { escapeValue: false },
});

export default i18n;
