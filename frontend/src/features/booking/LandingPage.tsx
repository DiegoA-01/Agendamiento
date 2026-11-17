import { useEffect, useState, type CSSProperties } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { SOCIAL_NETWORKS } from "../../shared/api/types";
import { formatMoney } from "../../shared/money";
import { Notice } from "../../shared/ui/primitives";
import { usePublicCompany, usePublicServices } from "./api";
import { DEMO_INTERVAL_MS, DEMO_STEPS, demoServices, nextDays, nextDemoStep } from "./howItWorks";
import { DEMO_DAY_INDEX, DEMO_TIME, PhoneDemo } from "./PhoneDemo";
import { todayIn } from "./wizard";

function prefersReducedMotion(): boolean {
  return globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

const delay = (ms: number) => ({ animationDelay: `${ms}ms` }) as CSSProperties;

/** Portada del negocio (spec §13) en verde esmeralda metalizado, como la tarjeta de la cita. Arriba,
 *  el nombre grande, el botón de reservar y un celular que hace la reserva solo; al confirmar, la
 *  tarjeta de la cita sale del celular. Debajo, los pasos sincronizados con el celular y la lista de
 *  servicios con precios. */
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
  const networks = SOCIAL_NETWORKS.filter((key) => company.social_links[key]);
  const services = demoServices(categories, 50);
  const first = services[0];
  const money = (value: string) => formatMoney(value, company.currency, i18n.language);
  const done = DEMO_STEPS[step] === "done";
  const demoDay = nextDays(todayIn(company.timezone), 5)[DEMO_DAY_INDEX];
  const demoDate = new Intl.DateTimeFormat(i18n.language, {
    weekday: "long",
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(`${demoDay}T12:00:00Z`));

  function show(index: number) {
    setStep(index);
    setPlaying(false);
  }

  return (
    <div className="landing">
      <section className="ld-wrap ld-hero">
        <div className="flex flex-col">
          {company.logo?.medium && (
            <img
              src={company.logo.medium}
              alt=""
              className="ld-in mb-6 size-20 rounded-2xl object-cover"
            />
          )}
          <h1 className="ld-title ld-in font-display" style={delay(100)}>
            {company.name}
          </h1>
          <p className="ld-lead ld-in" style={delay(250)}>
            {t("booking.home.lead")}
          </p>
          {company.booking_enabled ? (
            <div
              className="ld-in mt-9 flex flex-wrap items-center gap-x-7 gap-y-4"
              style={delay(400)}
            >
              <Link to="/reservar" className="ld-cta">
                {t("booking.cta")} <span aria-hidden="true">→</span>
              </Link>
              <a href="#servicios" className="ld-link">
                {t("booking.home.seeServices")}
              </a>
            </div>
          ) : (
            <div className="ld-in mt-8" style={delay(400)}>
              <Notice tone="warning">{t("booking.disabled")}</Notice>
            </div>
          )}
          <dl className="ld-facts ld-in" style={delay(550)}>
            <div>
              <dt>{t("booking.home.facts.minuteLabel")}</dt>
              <dd>{t("booking.home.facts.minute")}</dd>
            </div>
            <div>
              <dt>{t("booking.home.facts.cancelLabel")}</dt>
              <dd>{t("booking.home.facts.cancel", { count: company.cancel_min_hours })}</dd>
            </div>
            <div>
              <dt>{t("booking.home.facts.accountLabel")}</dt>
              <dd>0</dd>
            </div>
          </dl>
          {company.phone && (
            <a
              href={`tel:${company.phone}`}
              className="ld-link ld-in mt-6 self-start"
              style={delay(650)}
            >
              {t("booking.home.call", { phone: company.phone })}
            </a>
          )}
        </div>

        <div className="ld-stage ld-in" style={delay(300)}>
          <div aria-hidden="true" className={`ld-card ${done ? "ld-card-out" : ""}`}>
            <div className="flex items-start justify-between gap-3 text-xs font-semibold tracking-[0.14em] uppercase">
              <span className="truncate">{company.name}</span>
              <span className="ld-pill">{t("booking.status.confirmed")}</span>
            </div>
            <span className="ld-chip" />
            <p className="ld-when first-letter:uppercase">
              {demoDate} · {DEMO_TIME}
            </p>
            <div className="mt-auto flex items-end justify-between gap-3">
              <span className="truncate text-xs tracking-[0.12em] uppercase">
                {first?.name ?? t("booking.home.demo.service1")}
              </span>
              {first && <span className="ld-total">{money(first.price)}</span>}
            </div>
          </div>
          <div aria-hidden="true" className={`ld-toast ${done ? "ld-toast-on" : ""}`}>
            <span className="ld-toast-dot">
              <svg
                viewBox="0 0 24 24"
                className="size-4"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m5 12.5 4.5 4.5L19 7.5" />
              </svg>
            </span>
            {t("booking.home.toast", { time: DEMO_TIME })}
          </div>
          <PhoneDemo
            step={DEMO_STEPS[step]}
            services={services.slice(0, 3)}
            currency={company.currency}
            timeZone={company.timezone}
            businessName={company.name}
          />
        </div>
      </section>

      <section className="ld-steps">
        <div className="ld-wrap">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="ld-h2 font-display">{t("booking.home.howTitle")}</h2>
              <p className="ld-sub">{t("booking.home.howSub")}</p>
            </div>
            <button
              type="button"
              onClick={() => setPlaying((value) => !value)}
              className="ld-ghost"
            >
              {t(playing ? "booking.home.pause" : "booking.home.play")}
            </button>
          </div>
          <ol className="ld-track">
            <li aria-hidden="true" className="ld-line">
              <i style={{ transform: `scaleX(${step / (DEMO_STEPS.length - 1)})` }} />
            </li>
            {DEMO_STEPS.map((key, index) => (
              <li key={key}>
                <button
                  type="button"
                  aria-current={index === step ? "step" : undefined}
                  onClick={() => show(index)}
                  className={`ld-step ${index === step ? "ld-step-on" : ""}`}
                >
                  <span className="ld-dot">{index + 1}</span>
                  <span className="mt-5 block text-xl font-semibold">
                    {t(`booking.home.steps.${key}.title`)}
                  </span>
                  <span className="mt-2 block text-base leading-relaxed opacity-75">
                    {t(`booking.home.steps.${key}.text`, { count: company.cancel_min_hours })}
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {services.length > 0 && (
        <section id="servicios" className="ld-services">
          <div className="ld-wrap">
            <h2 className="ld-h2 font-display">{t("booking.home.servicesTitle")}</h2>
            <ul className="mt-10">
              {services.map((service) => (
                <li key={service.id}>
                  <Link
                    to={company.booking_enabled ? "/reservar" : "#servicios"}
                    className="ld-service"
                  >
                    <span className="font-display">{service.name}</span>
                    <span className="ld-service-min">
                      {t("booking.home.demo.minutes", { count: service.duration_min })}
                    </span>
                    <span className="ld-service-price">{money(service.price)}</span>
                  </Link>
                </li>
              ))}
            </ul>
            {networks.length > 0 && (
              <ul className="mt-12 flex flex-wrap gap-5 text-sm">
                {networks.map((key) => (
                  <li key={key}>
                    <a
                      href={company.social_links[key]}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ld-link"
                    >
                      {t(`catalog.company.networks.${key}`)}
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
