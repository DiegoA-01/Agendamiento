import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { BrandMark } from "../../shared/ui/brand";
import { DARK_GLASS } from "../../shared/ui/brandStyles";
import { LanguageSwitcher } from "../../shared/ui/LanguageSwitcher";
import { termsSections } from "./terms";

export const PLATFORM_TERMS_PATH = "/condiciones-de-uso";

/** Condiciones de uso de la plataforma (S8). Texto fijo en las traducciones, igual en todos los
 *  hosts: lo leen el Super Admin y el equipo de cada negocio, no los clientes que reservan. Es un
 *  documento de la plataforma, así que se arma como su panel: índice en la tarjeta oscura y el
 *  texto en vidrio claro. */
export function PlatformTermsPage() {
  const { t } = useTranslation();
  const sections = termsSections(t);
  const anchor = (index: number) => `seccion-${index + 1}`;
  return (
    <div className="platform min-h-screen p-3 sm:p-4">
      <div className="mx-auto flex max-w-[1240px] gap-5">
        <aside className="sticky top-4 hidden h-[calc(100vh-2rem)] w-[272px] shrink-0 lg:block">
          <nav
            aria-label={t("platformTerms.contents")}
            className={`flex h-full flex-col gap-6 overflow-y-auto p-4 ${DARK_GLASS}`}
          >
            <Link to="/login" className="px-1 pt-1">
              <BrandMark />
            </Link>
            <div className="flex flex-col gap-1">
              <p className="px-3 text-sm text-white/55">{t("platformTerms.contents")}</p>
              {sections.map((section, index) => (
                <a
                  key={section.title}
                  href={`#${anchor(index)}`}
                  className="rounded-2xl px-3 py-2 text-sm text-white/85 hover:bg-white/10 hover:text-white"
                >
                  {section.title}
                </a>
              ))}
            </div>
            <Link
              to="/login"
              className="metal mt-auto rounded-2xl px-4 py-3 text-center font-semibold"
            >
              {t("platformTerms.back")}
            </Link>
          </nav>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col gap-5">
          <header className="glass flex items-center justify-between gap-3 rounded-[24px] border px-5 py-3">
            <Link to="/login" className="lg:invisible" aria-label={t("platformTerms.back")}>
              <BrandMark />
            </Link>
            <LanguageSwitcher />
          </header>

          <article className="glass platform-main flex flex-col gap-8 rounded-[28px] border p-6 sm:p-10">
            <header className="flex flex-col gap-2">
              <h1 className="sm:!text-4xl">{t("platformTerms.title")}</h1>
              <p className="text-[var(--pf-muted)]">{t("platformTerms.updated")}</p>
            </header>
            <p
              role="note"
              className="rounded-2xl bg-amber-50/90 px-5 py-4 text-amber-950 ring-1 ring-amber-200"
            >
              {t("platformTerms.draftNotice")}
            </p>
            {sections.map((section, index) => (
              <section
                key={section.title}
                id={anchor(index)}
                className="flex scroll-mt-6 flex-col gap-3"
              >
                <h2 className="text-xl font-semibold tracking-tight">{section.title}</h2>
                {section.body.map((paragraph) => (
                  <p key={paragraph} className="leading-relaxed">
                    {paragraph}
                  </p>
                ))}
              </section>
            ))}
          </article>

          <Link
            to="/login"
            className="metal self-start rounded-2xl px-5 py-3 font-semibold focus-visible:outline-2 lg:hidden"
          >
            {t("platformTerms.back")}
          </Link>
        </div>
      </div>
    </div>
  );
}
