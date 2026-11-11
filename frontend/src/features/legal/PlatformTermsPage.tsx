import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { LanguageSwitcher } from "../../shared/ui/LanguageSwitcher";
import { Notice } from "../../shared/ui/primitives";
import { termsSections } from "./terms";

export const PLATFORM_TERMS_PATH = "/condiciones-de-uso";

/** Condiciones de uso de la plataforma (S8). Texto fijo en las traducciones, igual en todos los
 *  hosts: lo leen el Super Admin y el equipo de cada negocio, no los clientes que reservan. */
export function PlatformTermsPage() {
  const { t } = useTranslation();
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-10">
      <div className="flex items-center justify-between gap-3">
        <span className="text-lg font-semibold text-slate-900">{t("app.name")}</span>
        <LanguageSwitcher />
      </div>
      <article className="flex flex-col gap-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <header className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold text-slate-900">{t("platformTerms.title")}</h1>
          <p className="text-sm text-slate-600">{t("platformTerms.updated")}</p>
        </header>
        <Notice tone="warning">{t("platformTerms.draftNotice")}</Notice>
        {termsSections(t).map((section) => (
          <section key={section.title} className="flex flex-col gap-2">
            <h2 className="text-lg font-semibold text-slate-900">{section.title}</h2>
            {section.body.map((paragraph) => (
              <p key={paragraph} className="leading-relaxed text-slate-800">
                {paragraph}
              </p>
            ))}
          </section>
        ))}
      </article>
      <Link to="/login" className="text-sm underline">
        {t("platformTerms.back")}
      </Link>
    </main>
  );
}
