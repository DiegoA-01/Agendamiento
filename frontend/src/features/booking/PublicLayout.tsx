import { useEffect, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, Outlet, useLocation } from "react-router-dom";
import { describeError } from "../../shared/api/errors";
import { ErrorBox, Loading } from "../../shared/ui/primitives";
import { usePublicCompany } from "./api";
import { CookieBanner } from "./CookieBanner";

/** Marco de las páginas públicas del negocio: logo, idioma del negocio, enlaces legales y aviso de
 *  cookies. Mobile-first. Todos los negocios usan el mismo estilo (blanco, vidrio y verde
 *  metalizado, clase `.booking` en index.css): el tema de colores del negocio ya no se aplica aquí.
 *  No hay selector de idioma: el sitio habla el del negocio. */
export function PublicLayout({ children }: { children?: ReactNode }) {
  const { t, i18n } = useTranslation();
  const company = usePublicCompany();
  // La portada (y la reserva, que se abre encima de ella) usa todo el ancho; el resto, una columna.
  const { pathname } = useLocation();
  const landing = pathname === "/" || pathname === "/reservar";
  const width = landing ? "max-w-[1280px]" : "max-w-2xl";
  const language = company.data?.language;

  useEffect(() => {
    if (language && i18n.language !== language) {
      void i18n.changeLanguage(language);
    }
  }, [language, i18n]);

  if (company.isPending) return <Loading />;
  if (company.isError) {
    return (
      <main className="mx-auto max-w-2xl p-4">
        <ErrorBox
          message={describeError(t, company.error)}
          onRetry={() => void company.refetch()}
        />
      </main>
    );
  }
  const { name, logo } = company.data;

  return (
    <div
      className={`booking flex min-h-dvh flex-col ${
        landing ? "public-dark" : "public-backdrop text-[var(--color-text)]"
      }`}
    >
      <a
        href="#contenido"
        className="sr-only rounded bg-white px-3 py-2 focus:not-sr-only focus:absolute focus:top-2 focus:left-2"
      >
        {t("nav.skip")}
      </a>
      <header className={`mx-auto w-full ${width} px-3 pt-3 sm:px-4`}>
        <div className="glass flex items-center gap-3 rounded-[22px] border px-4 py-3">
          <Link to="/" className="flex min-w-0 flex-1 items-center gap-3">
            {logo?.thumb ? (
              <img src={logo.thumb} alt="" className="size-10 shrink-0 rounded-xl object-cover" />
            ) : (
              <span
                aria-hidden="true"
                className="metal flex size-10 shrink-0 items-center justify-center rounded-xl font-bold"
              >
                {name.trim().charAt(0).toUpperCase()}
              </span>
            )}
            <span className="truncate text-lg font-semibold">{name}</span>
          </Link>
        </div>
      </header>
      <main
        id="contenido"
        className={
          landing ? "w-full flex-1" : `mx-auto w-full ${width} flex-1 px-4 py-6 pb-32 lg:py-10`
        }
      >
        {children ?? <Outlet />}
      </main>
      <footer className="px-4 py-6 text-sm">
        <nav
          aria-label={t("booking.legalNav")}
          className={`mx-auto flex ${width} flex-wrap gap-x-4 gap-y-2`}
        >
          <Link to="/terminos" className="underline">
            {t("booking.pages.terms.title")}
          </Link>
          <Link to="/privacidad" className="underline">
            {t("booking.pages.privacy.title")}
          </Link>
          <Link to="/cookies" className="underline">
            {t("booking.pages.cookies.title")}
          </Link>
          <Link to="/login" className="ml-auto opacity-70 hover:opacity-100">
            {t("booking.staffLogin")}
          </Link>
        </nav>
      </footer>
      <CookieBanner />
    </div>
  );
}
