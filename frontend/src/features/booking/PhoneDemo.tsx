import { useTranslation } from "react-i18next";
import type { PublicService } from "../../shared/api/types";
import { formatMoney } from "../../shared/money";
import { DEMO_STEPS, nextDays, type DemoStep } from "./howItWorks";
import { todayIn } from "./wizard";

/** Horas de ejemplo del paso 2: tres antes del descanso y tres después. */
const BEFORE = ["12:00", "12:15", "12:30"];
const AFTER = ["14:00", "14:15", "14:30"];
export const DEMO_TIME = "14:00";
export const DEMO_DAY_INDEX = 2;

/** Celular dibujado con CSS que enseña la reserva pantalla por pantalla, en el verde esmeralda
 *  metalizado de la tarjeta de la cita. Es ilustrativo: los mismos pasos van en texto debajo, así
 *  que queda oculto para lectores de pantalla. Usa los primeros servicios reales del negocio. */
export function PhoneDemo({
  step,
  services,
  currency,
  timeZone,
  businessName,
}: {
  step: DemoStep;
  services: PublicService[];
  currency: string;
  timeZone: string;
  businessName: string;
}) {
  const index = DEMO_STEPS.indexOf(step);

  return (
    <div aria-hidden="true" className="ld-phone">
      <div className="ld-screen">
        <span className="ld-island" />
        <div className="flex justify-between px-2 text-[11px] font-semibold">
          <span>9:41</span>
          <span>●●●</span>
        </div>
        <div className="mt-6 mb-3 flex items-center gap-2 text-[13px] font-semibold">
          <span className="ld-mark size-7 text-xs">
            {businessName.trim().charAt(0).toUpperCase()}
          </span>
          <span className="truncate">{businessName}</span>
        </div>
        <div className="flex gap-1.5">
          {[0, 1, 2].map((bar) => (
            <i key={bar} className={`ld-bar ${bar <= Math.min(index, 2) ? "ld-bar-on" : ""}`} />
          ))}
        </div>
        {DEMO_STEPS.map((name, i) => (
          <div key={name} className={`ld-view ${i === index ? "ld-view-on" : ""}`}>
            {name === "services" && <ServicesScreen services={services} currency={currency} />}
            {name === "schedule" && <ScheduleScreen timeZone={timeZone} />}
            {name === "details" && <DetailsScreen />}
            {name === "done" && <DoneScreen />}
          </div>
        ))}
      </div>
    </div>
  );
}

function Title({ children }: { children: string }) {
  return <p className="font-display text-xl leading-tight font-semibold">{children}</p>;
}

function ServicesScreen({ services, currency }: { services: PublicService[]; currency: string }) {
  const { t, i18n } = useTranslation();
  const rows =
    services.length > 0
      ? services.map((s) => ({
          id: s.id,
          name: s.name,
          meta: `${t("booking.home.demo.minutes", { count: s.duration_min })} · ${formatMoney(s.price, currency, i18n.language)}`,
        }))
      : [1, 2, 3].map((n) => ({
          id: String(n),
          name: t(`booking.home.demo.service${n}`),
          meta: t("booking.home.demo.minutes", { count: 30 }),
        }));
  return (
    <>
      <Title>{t("booking.wizard.steps.services")}</Title>
      {rows.map((row, i) => (
        <div key={row.id} className={`ld-row ${i === 0 ? "ld-sel" : ""}`}>
          <span className="min-w-0">
            <span className="block truncate">{row.name}</span>
            <small className="block truncate">{row.meta}</small>
          </span>
          <span className="ld-tick" />
        </div>
      ))}
      <span className="ld-btn">{t("booking.wizard.continue")}</span>
    </>
  );
}

function ScheduleScreen({ timeZone }: { timeZone: string }) {
  const { t, i18n } = useTranslation();
  const days = nextDays(todayIn(timeZone), 5);
  const weekday = new Intl.DateTimeFormat(i18n.language, { weekday: "short", timeZone: "UTC" });
  return (
    <>
      <Title>{t("booking.wizard.steps.schedule")}</Title>
      <div className="grid grid-cols-5 gap-1.5">
        {days.map((day, i) => (
          <span key={day} className={`ld-day ${i === DEMO_DAY_INDEX ? "ld-sel" : ""}`}>
            {weekday.format(new Date(`${day}T12:00:00Z`)).replace(".", "")}
            <b>{Number(day.slice(8))}</b>
          </span>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-1.5">
        {BEFORE.map((time) => (
          <span key={time} className="ld-time">
            {time}
          </span>
        ))}
        <span className="ld-break col-span-3">{t("booking.wizard.break")} 13:00 – 14:00</span>
        {AFTER.map((time) => (
          <span key={time} className={`ld-time ${time === DEMO_TIME ? "ld-sel" : ""}`}>
            {time}
          </span>
        ))}
      </div>
      <span className="ld-btn">{t("booking.wizard.continue")}</span>
    </>
  );
}

function DetailsScreen() {
  const { t } = useTranslation();
  return (
    <>
      <Title>{t("booking.wizard.steps.details")}</Title>
      {(["name", "phone"] as const).map((field) => (
        <span key={field} className="text-[11px] opacity-70">
          {t(`booking.home.demo.${field}Label`)}
          <span className="ld-input">{t(`booking.home.demo.${field}Value`)}</span>
        </span>
      ))}
      <span className="ld-btn">{t("booking.wizard.confirm")}</span>
    </>
  );
}

function DoneScreen() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
      <svg viewBox="0 0 52 52" className="ld-seal size-16">
        <circle cx="26" cy="26" r="24" />
        <path d="M15 27l7.5 7.5L37.5 19" />
      </svg>
      <Title>{t("booking.home.demo.doneTitle")}</Title>
      <p className="text-xs opacity-70">{t("booking.home.demo.doneText")}</p>
    </div>
  );
}
