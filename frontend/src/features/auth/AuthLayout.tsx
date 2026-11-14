import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { isPlatformHost } from "../../shared/host";
import { BrandMark } from "../../shared/ui/brand";
import { DARK_GLASS } from "../../shared/ui/brandStyles";
import { LanguageSwitcher } from "../../shared/ui/LanguageSwitcher";
import { usePublicCompany } from "../booking/api";
import { PLATFORM_TERMS_PATH } from "../legal/PlatformTermsPage";

/** Login, recuperación y cambio de contraseña con el mismo vidrio del panel al que se entra: verde
 *  metalizado en el host del Super Admin y púrpura con vidrio líquido en el de cada negocio. */
export function AuthLayout({ title, children }: { title: string; children: ReactNode }) {
  return isPlatformHost() ? (
    <GlassAuthLayout variant="platform" title={title}>
      {children}
    </GlassAuthLayout>
  ) : (
    <BusinessAuthLayout title={title}>{children}</BusinessAuthLayout>
  );
}

function BusinessAuthLayout({ title, children }: { title: string; children: ReactNode }) {
  const company = usePublicCompany().data;
  return (
    <GlassAuthLayout variant="business" title={title} businessName={company?.name}>
      {children}
    </GlassAuthLayout>
  );
}

const PITCH = {
  platform: ["auth.adminPitch1", "auth.adminPitch2", "auth.adminPitch3"],
  business: ["auth.businessPitch1", "auth.businessPitch2", "auth.businessPitch3"],
} as const;

function GlassAuthLayout({
  variant,
  title,
  businessName,
  children,
}: {
  variant: "platform" | "business";
  title: string;
  businessName?: string;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const business = variant === "business";
  // El Super Admin usa la tarjeta oscura de su barra lateral; el negocio, el vidrio líquido claro.
  const aside = business
    ? "liquid-glass hidden flex-col justify-between gap-10 p-8 lg:flex"
    : `hidden flex-col justify-between gap-10 p-8 lg:flex ${DARK_GLASS}`;
  const soft = business ? "text-[var(--pf-muted)]" : "text-white/85";
  const linkTone = business
    ? "text-[var(--pf-muted)] hover:text-[var(--pf-ink)]"
    : "text-white/60 hover:text-white";

  return (
    <div className={`platform min-h-screen p-3 sm:p-4 ${business ? "owner" : ""}`}>
      <div className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-[1200px] gap-4 lg:grid-cols-[minmax(0,440px)_1fr]">
        <aside className={aside}>
          <BrandMark size="lg" name={businessName} />
          <div className="flex flex-col gap-6">
            <p className="text-4xl leading-tight font-bold tracking-tight">
              {t(business ? "auth.businessPitchTitle" : "auth.adminPitchTitle")}
            </p>
            <ul className={`flex flex-col gap-3 ${soft}`}>
              {PITCH[variant].map((key) => (
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
          <Link to={PLATFORM_TERMS_PATH} className={`text-sm underline ${linkTone}`}>
            {t("platformTerms.link")}
          </Link>
        </aside>

        <main className="flex flex-col items-center justify-center gap-6 py-8">
          <div className="flex w-full max-w-md items-center justify-between gap-3">
            <span className="min-w-0 lg:invisible">
              <BrandMark name={businessName} />
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
