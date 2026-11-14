import { useTranslation } from "react-i18next";
import type { PublicService } from "../../shared/api/types";
import { formatMoney } from "../../shared/money";
import { DEMO_STEPS, nextDays, type DemoStep } from "./howItWorks";
import { todayIn } from "./wizard";

const TIMES = ["9:00", "10:30", "11:00", "15:30"];

/** Celular dibujado con CSS que enseña la reserva pantalla por pantalla. Es ilustrativo: los mismos
 *  pasos van en texto al lado, así que el celular queda oculto para lectores de pantalla. Usa los
 *  colores del tema del negocio y, si los hay, sus primeros servicios reales. */
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
  const { t } = useTranslation();
  const index = DEMO_STEPS.indexOf(step);

  return (
    <div aria-hidden="true" className="phone-demo relative mx-auto w-[300px] shrink-0 sm:w-[320px]">
      <div className="phone-frame rounded-[52px] p-3">
        <div className="relative flex h-[560px] flex-col overflow-hidden rounded-[42px] bg-[var(--color-background)] text-[var(--color-text)] sm:h-[580px]">
          <div className="absolute top-2.5 left-1/2 h-6 w-24 -translate-x-1/2 rounded-full bg-black" />
          <div className="flex items-center justify-between px-7 pt-3 text-[11px] font-semibold opacity-80">
            <span>9:41</span>
            <span className="tracking-widest">●●●</span>
          </div>

          <div className="flex items-center gap-2 px-5 pt-6 pb-3">
            <span className="flex size-8 items-center justify-center rounded-xl bg-[var(--color-primary)] text-sm font-bold text-[var(--color-background)]">
              {businessName.trim().charAt(0).toUpperCase()}
            </span>
            <span className="truncate text-sm font-semibold">{businessName}</span>
          </div>

          {step !== "done" && (
            <div className="px-5">
              <p className="text-[11px] text-[var(--bk-muted)]">
                {t("booking.wizard.stepOf", { step: index + 1, total: 3 })}
              </p>
              <div className="mt-1.5 flex gap-1.5">
                {[0, 1, 2].map((bar) => (
                  <span
                    key={bar}
                    className={`h-1 flex-1 rounded-full transition-colors duration-500 ${
                      bar <= index ? "bg-[var(--color-primary)]" : "bg-[var(--bk-raised)]"
                    }`}
                  />
                ))}
              </div>
            </div>
          )}

          <div key={step} className="phone-screen flex flex-1 flex-col gap-3 px-5 pt-4 pb-5">
            {step === "services" && <ServicesScreen services={services} currency={currency} />}
            {step === "schedule" && <ScheduleScreen timeZone={timeZone} />}
            {step === "details" && <DetailsScreen />}
            {step === "done" && <DoneScreen />}
          </div>
        </div>
      </div>
    </div>
  );
}

function ScreenTitle({ children }: { children: string }) {
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
      <ScreenTitle>{t("booking.wizard.steps.services")}</ScreenTitle>
      <div className="flex flex-col gap-2">
        {rows.map((row, i) => (
          <div
            key={row.id}
            className={`flex items-center gap-3 rounded-2xl border px-3 py-3 ${
              i === 0
                ? "border-[var(--color-primary)] bg-[var(--bk-raised)]"
                : "border-[var(--bk-line)]"
            }`}
          >
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold">{row.name}</span>
              <span className="block truncate text-[11px] text-[var(--bk-muted)]">{row.meta}</span>
            </span>
            <span
              className={`flex size-5 shrink-0 items-center justify-center rounded-full border text-[11px] ${
                i === 0
                  ? "border-[var(--color-primary)] bg-[var(--color-primary)] text-[var(--color-background)]"
                  : "border-[var(--bk-line)]"
              }`}
            >
              {i === 0 && <Check className="size-3" />}
            </span>
          </div>
        ))}
      </div>
      <FakeButton>{t("booking.wizard.continue")}</FakeButton>
    </>
  );
}

function ScheduleScreen({ timeZone }: { timeZone: string }) {
  const { t, i18n } = useTranslation();
  const days = nextDays(todayIn(timeZone), 5);
  const weekday = new Intl.DateTimeFormat(i18n.language, { weekday: "short", timeZone: "UTC" });
  return (
    <>
      <ScreenTitle>{t("booking.wizard.steps.schedule")}</ScreenTitle>
      <div className="flex gap-2">
        <span className="rounded-full bg-[var(--color-primary)] px-3 py-1.5 text-[11px] font-semibold text-[var(--color-background)]">
          {t("booking.home.demo.anyPro")}
        </span>
        <span className="rounded-full border border-[var(--bk-line)] px-3 py-1.5 text-[11px]">
          {t("booking.home.demo.pro")}
        </span>
      </div>
      <div className="grid grid-cols-5 gap-1.5">
        {days.map((day, i) => (
          <span
            key={day}
            className={`flex flex-col items-center rounded-xl py-2 text-[11px] ${
              i === 1
                ? "bg-[var(--color-primary)] font-semibold text-[var(--color-background)]"
                : "bg-[var(--bk-raised)]"
            }`}
          >
            <span className="capitalize">
              {weekday.format(new Date(`${day}T12:00:00Z`)).replace(".", "")}
            </span>
            <span className="text-base font-semibold">{Number(day.slice(8))}</span>
          </span>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2">
        {TIMES.map((time, i) => (
          <span
            key={time}
            className={`rounded-xl border py-2 text-center text-sm tabular-nums ${
              i === 1
                ? "border-[var(--color-primary)] bg-[var(--bk-raised)] font-semibold"
                : "border-[var(--bk-line)]"
            }`}
          >
            {time}
          </span>
        ))}
      </div>
      <FakeButton>{t("booking.wizard.continue")}</FakeButton>
    </>
  );
}

function DetailsScreen() {
  const { t } = useTranslation();
  return (
    <>
      <ScreenTitle>{t("booking.wizard.steps.details")}</ScreenTitle>
      {(["name", "phone"] as const).map((field) => (
        <div key={field} className="flex flex-col gap-1">
          <span className="text-[11px] text-[var(--bk-muted)]">
            {t(`booking.home.demo.${field}Label`)}
          </span>
          <span className="rounded-xl border border-[var(--bk-line)] bg-[var(--color-surface)] px-3 py-2.5 text-sm">
            {t(`booking.home.demo.${field}Value`)}
          </span>
        </div>
      ))}
      <FakeButton>{t("booking.wizard.confirm")}</FakeButton>
    </>
  );
}

function DoneScreen() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center">
      <span className="flex size-16 items-center justify-center rounded-full bg-[var(--color-primary)] text-3xl text-[var(--color-background)]">
        <Check className="size-8" />
      </span>
      <ScreenTitle>{t("booking.home.demo.doneTitle")}</ScreenTitle>
      <p className="text-sm text-[var(--bk-muted)]">{t("booking.home.demo.doneText")}</p>
    </div>
  );
}

function FakeButton({ children }: { children: string }) {
  return (
    <span className="mt-auto block rounded-2xl bg-[var(--color-primary)] py-3 text-center text-sm font-semibold text-[var(--color-background)]">
      {children}
    </span>
  );
}

function Check({ className }: { className: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m5 12.5 4.5 4.5L19 7.5" />
    </svg>
  );
}
