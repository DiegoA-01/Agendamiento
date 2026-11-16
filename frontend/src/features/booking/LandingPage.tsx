import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { SOCIAL_NETWORKS } from "../../shared/api/types";
import { formatMoney } from "../../shared/money";
import { Notice } from "../../shared/ui/primitives";
import { usePublicCompany, usePublicServices } from "./api";
import { DEMO_INTERVAL_MS, DEMO_STEPS, demoServices, nextDemoStep } from "./howItWorks";
import { PhoneDemo } from "./PhoneDemo";

function prefersReducedMotion(): boolean {
  return globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

/** Portada del negocio (spec §13): quién es, cómo se reserva y el botón de reservar. Ocupa toda la
 *  pantalla: a un lado los pasos en texto y al otro un celular que los va mostrando. */
export default function LandingPage() {
  const { t, i18n } = useTranslation();
  const company = usePublicCompany().data;
  const categories = usePublicServices().data;
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(() => !prefersReducedMotion());

  useEffect(() => {
    if (!playing) return;
    const timer = globalThis.setInterval(() => setStep(nextDemoStep), DEMO_INTERVAL_MS);
    return () => globalThis.clearInterval(timer);
  }, [playing]);

  if (!company) return null;
  const place = [company.address, company.city].filter(Boolean).join(", ");
  const networks = SOCIAL_NETWORKS.filter((key) => company.social_links[key]);
  const services = demoServices(categories, 6);

  function show(index: number) {
    setStep(index);
    setPlaying(false);
  }

  return (
    <div className="flex flex-col gap-20">
      <section className="grid items-center gap-12 lg:min-h-[calc(100dvh-14rem)] lg:grid-cols-[minmax(0,1fr)_auto] lg:gap-20">
        <div className="flex flex-col gap-8">
          <div className="flex flex-col gap-4">
            {company.logo?.medium && (
              <img src={company.logo.medium} alt="" className="size-20 rounded-2xl object-cover" />
            )}
            {place && (
              <p className="text-sm tracking-wide text-[var(--bk-muted)] uppercase">{place}</p>
            )}
            <h1 className="font-display text-5xl leading-[1.05] font-semibold tracking-tight sm:text-6xl">
              {company.name}
            </h1>
            <p className="max-w-[46ch] text-lg text-[var(--bk-muted)]">
              {t("booking.home.tagline")}
            </p>
          </div>

          {company.booking_enabled ? (
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
              <Link
                to="/reservar"
                className="metal inline-flex min-h-14 items-center rounded-2xl px-8 text-lg font-semibold transition-transform focus-visible:outline-2 active:scale-[0.98]"
              >
                {t("booking.cta")}
              </Link>
              {company.phone && (
                <a href={`tel:${company.phone}`} className="text-sm underline">
                  {t("booking.home.call", { phone: company.phone })}
                </a>
              )}
            </div>
          ) : (
            <Notice tone="warning">{t("booking.disabled")}</Notice>
          )}

          <div className="glass flex flex-col gap-3 rounded-[26px] border p-4 sm:p-5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold tracking-wide uppercase">
                {t("booking.home.howTitle")}
              </h2>
              <button
                type="button"
                onClick={() => setPlaying((value) => !value)}
                className="rounded-full border border-[var(--bk-line)] bg-white/70 px-3 py-1 text-xs focus-visible:outline-2"
              >
                {t(playing ? "booking.home.pause" : "booking.home.play")}
              </button>
            </div>
            <ol className="flex flex-col gap-2">
              {DEMO_STEPS.map((key, index) => {
                const active = index === step;
                return (
                  <li key={key}>
                    <button
                      type="button"
                      aria-current={active ? "step" : undefined}
                      onClick={() => show(index)}
                      className={`flex w-full items-start gap-4 rounded-2xl border px-4 py-3 text-left transition-colors focus-visible:outline-2 ${
                        active ? "step-active border-white" : "border-transparent hover:bg-white/50"
                      }`}
                    >
                      <span
                        className={`flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
                          active ? "metal" : "border border-[var(--bk-line)] bg-white/60"
                        }`}
                      >
                        {index + 1}
                      </span>
                      <span className="flex flex-col">
                        <span className="font-semibold">
                          {t(`booking.home.steps.${key}.title`)}
                        </span>
                        <span className="text-sm text-[var(--bk-muted)]">
                          {t(`booking.home.steps.${key}.text`, {
                            count: company.cancel_min_hours,
                          })}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ol>
          </div>
        </div>

        <PhoneDemo
          step={DEMO_STEPS[step]}
          services={services.slice(0, 3)}
          currency={company.currency}
          timeZone={company.timezone}
          businessName={company.name}
        />
      </section>

      {services.length > 0 && (
        <section className="flex flex-col gap-6">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h2 className="font-display text-3xl font-semibold">
              {t("booking.home.servicesTitle")}
            </h2>
            {company.booking_enabled && (
              <Link to="/reservar" className="text-sm underline">
                {t("booking.home.seeAll")}
              </Link>
            )}
          </div>
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {services.map((service) => (
              <li
                key={service.id}
                className="glass flex flex-col gap-1 rounded-[20px] border px-5 py-4"
              >
                <span className="font-semibold">{service.name}</span>
                <span className="text-sm text-[var(--bk-muted)]">
                  {t("booking.home.demo.minutes", { count: service.duration_min })} ·{" "}
                  {formatMoney(service.price, company.currency, i18n.language)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {networks.length > 0 && (
        <ul className="flex flex-wrap gap-3 text-sm">
          {networks.map((key) => (
            <li key={key}>
              <a
                href={company.social_links[key]}
                target="_blank"
                rel="noopener noreferrer"
                className="underline"
              >
                {t(`catalog.company.networks.${key}`)}
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
