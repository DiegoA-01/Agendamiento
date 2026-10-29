import { useTranslation } from "react-i18next";
import { SUPPORTED_LANGUAGES, setLanguage, type Language } from "../i18n";

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  return (
    <label className="flex items-center gap-2 text-sm">
      <span>{t("language.label")}</span>
      <select
        className="rounded border px-2 py-1"
        value={i18n.language}
        onChange={(e) => void setLanguage(e.target.value as Language)}
      >
        {SUPPORTED_LANGUAGES.map((lang) => (
          <option key={lang} value={lang}>
            {t(`language.${lang}`)}
          </option>
        ))}
      </select>
    </label>
  );
}
