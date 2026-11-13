import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { isPlatformHost } from "../../shared/host";
import { BrandMark } from "../../shared/ui/brand";
import { DARK_GLASS } from "../../shared/ui/brandStyles";
import { LanguageSwitcher } from "../../shared/ui/LanguageSwitcher";
import { Card } from "../../shared/ui/primitives";
import { PLATFORM_TERMS_PATH } from "../legal/PlatformTermsPage";

/** Tarjeta centrada para login, recuperación y cambio de contraseña. En el host del Super Admin
 *  usa el vidrio y el verde metalizado de su panel. */
export function AuthLayout({ title, children }: { title: string; children: ReactNode }) {
  return isPlatformHost() ? (
    <PlatformAuthLayout title={title}>{children}</PlatformAuthLayout>
  ) : (
    <BusinessAuthLayout title={title}>{children}</BusinessAuthLayout>
  );
}

function BusinessAuthLayout({ title, children }: { title: string; children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center gap-6 px-4 py-10">
      <div className="flex items-center justify-between">
        <span className="text-lg font-semibold text-slate-900">{t("app.name")}</span>
        <LanguageSwitcher />
      </div>
      <Card className="flex flex-col gap-5 p-6">
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
        {children}
      </Card>
      <Link to={PLATFORM_TERMS_PATH} className="text-center text-sm text-slate-600 underline">
        {t("platformTerms.link")}
      </Link>
    </main>
  );
}

const PITCH = ["auth.adminPitch1", "auth.adminPitch2", "auth.adminPitch3"] as const;

function PlatformAuthLayout({ title, children }: { title: string; children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <div className="platform min-h-screen p-3 sm:p-4">
      <div className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-[1200px] gap-4 lg:grid-cols-[minmax(0,440px)_1fr]">
        <aside className={`hidden flex-col justify-between gap-10 p-8 lg:flex ${DARK_GLASS}`}>
          <BrandMark size="lg" />
          <div className="flex flex-col gap-6">
            <p className="text-4xl leading-tight font-bold tracking-tight">
              {t("auth.adminPitchTitle")}
            </p>
            <ul className="flex flex-col gap-3 text-white/85">
              {PITCH.map((key) => (
                <li key={key} className="flex items-start gap-3">
                  <span
                    aria-hidden="true"
                    className="metal mt-1.5 size-2.5 shrink-0 rounded-full"
                  />
                  {t(key)}
                </li>
              ))}
            </ul>
          </div>
          <Link
            to={PLATFORM_TERMS_PATH}
            className="text-sm text-white/60 underline hover:text-white"
          >
            {t("platformTerms.link")}
          </Link>
        </aside>

        <main className="flex flex-col items-center justify-center gap-6 py-8">
          <div className="flex w-full max-w-md items-center justify-between gap-3">
            <span className="lg:invisible">
              <BrandMark />
            </span>
            <LanguageSwitcher />
          </div>
          <section className="glass platform-main flex w-full max-w-md flex-col gap-5 rounded-[28px] border p-7">
            <h1>{title}</h1>
            {children}
          </section>
          <Link
            to={PLATFORM_TERMS_PATH}
            className="text-sm text-[var(--pf-muted)] underline lg:hidden"
          >
            {t("platformTerms.link")}
          </Link>
        </main>
      </div>
    </div>
  );
}
