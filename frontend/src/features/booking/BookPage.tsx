import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ApiError, api } from "../../shared/api/client";
import { describeError } from "../../shared/api/errors";
import type {
  PublicBooked,
  PublicCategory,
  PublicProfessional,
  PublicService,
} from "../../shared/api/types";
import { formatMoney } from "../../shared/money";
import {
  CheckboxField,
  EmptyState,
  ErrorBox,
  Loading,
  Notice,
  TextField,
} from "../../shared/ui/primitives";
import {
  useAvailableDays,
  usePublicCompany,
  usePublicProfessionals,
  usePublicServices,
  useSlots,
} from "./api";
import { CancelAppointment } from "./CancelAppointment";
import { AppointmentSummary } from "./ManagePage";
import { ServiceDetail } from "./ServiceDetail";
import {
  MAX_SERVICES,
  PERIODS,
  STEPS,
  addMonths,
  bookingPayload,
  calendarCells,
  DAY_STYLES,
  dayStatuses,
  formatDay,
  formatTime,
  looksLikePhone,
  monthOf,
  selectedServices,
  slotsByPeriod,
  todayIn,
  toggleService,
  tokenFromManageUrl,
  totals,
  type Customer,
  type Step,
} from "./wizard";

const ANY = "any";

// Colores de la reserva (R9): solo los cinco del tema del negocio y sus mezclas (`.booking` en
// index.css). Lo elegido se marca invirtiendo tinta y fondo; el color principal va en la hora, el
// precio y el botón de seguir.
const INK = "text-[var(--color-text)]";
const MUTED = "text-[var(--bk-muted)]";
const PANEL = "bg-[var(--color-surface)]";
const RAISED = "bg-[var(--bk-raised)]";
const INVERSE = "bg-[var(--color-text)] text-[var(--color-background)]";
const ACCENT = "bg-[var(--color-primary)] text-[var(--color-background)]";
const PRESS = "transition-[transform,background-color,color] active:scale-[0.98]";
const SECTION_TITLE = "font-display text-2xl leading-tight";

function useCompanyFormat() {
  const { i18n } = useTranslation();
  const company = usePublicCompany().data;
  const timeZone = company?.timezone ?? "America/Bogota";
  const currency = company?.currency ?? "COP";
  return {
    timeZone,
    money: (value: string) => formatMoney(value, currency, i18n.language),
    time: (iso: string) => formatTime(iso, i18n.language, timeZone),
  };
}

// --- La reserva hasta ahora --------------------------------------------------------------------

/** Lo elegido hasta el momento, fijo arriba mientras se baja (R9). Es lo único que repite la
 *  selección: el paso de datos ya no trae otro resumen. */
function Ticket({
  services,
  who,
  when,
  minutes,
  price,
  note,
  forName,
}: {
  services: string;
  forName?: string;
  who: string;
  when: string;
  minutes: number;
  price: string;
  note?: string;
}) {
  const { t } = useTranslation();
  const detail = [who, when].filter(Boolean).join(" · ");
  return (
    <section
      aria-label={t("booking.wizard.ticket")}
      aria-live="polite"
      className={`sticky top-0 z-10 -mx-4 bg-[var(--color-background)] px-4 pt-1 pb-3`}
    >
      <div className={`rounded-2xl ${PANEL} px-4 py-3`}>
        <p className={`text-sm ${MUTED}`}>
          {t("booking.wizard.ticket")}
          {forName ? ` · ${t("booking.wizard.forName", { name: forName })}` : ""}
        </p>
        <p className="font-display mt-0.5 line-clamp-2 text-2xl leading-tight">
          {services || t("booking.wizard.ticketEmpty")}
        </p>
        <p className={`mt-0.5 truncate text-sm first-letter:uppercase ${MUTED}`}>
          {detail || t("booking.wizard.ticketPick")}
        </p>
        {minutes > 0 && (
          <div className="mt-2 flex items-baseline justify-between gap-3">
            <span className={`text-sm ${MUTED}`}>
              {t("booking.wizard.min", { count: minutes })}
            </span>
            <span className="font-display text-2xl text-[var(--color-primary)] tabular-nums">
              {price}
            </span>
          </div>
        )}
        {note && <p className={`mt-1 text-xs ${MUTED}`}>{note}</p>}
      </div>
    </section>
  );
}

// --- Paso 1: servicios --------------------------------------------------------------------------

function ServicesStep({
  categories,
  selected,
  onToggle,
}: {
  categories: PublicCategory[];
  selected: string[];
  onToggle: (id: string) => void;
}) {
  const { t } = useTranslation();
  const { money } = useCompanyFormat();
  const [detail, setDetail] = useState<PublicService | null>(null);
  if (categories.length === 0) return <EmptyState>{t("booking.wizard.noServices")}</EmptyState>;
  return (
    <div className="flex flex-col gap-8">
      {categories.map((category) => (
        <section key={category.id} className="flex flex-col gap-3">
          <div className="flex flex-wrap items-baseline justify-between gap-x-3">
            <h2 className={SECTION_TITLE}>{category.name}</h2>
            {category.single_choice && (
              <p className={`text-sm ${MUTED}`}>{t("booking.wizard.chooseOne")}</p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            {category.services.map((service) => {
              const isSelected = selected.includes(service.id);
              const blocked =
                !isSelected &&
                selected.length >= MAX_SERVICES &&
                !(category.single_choice && category.services.some((s) => selected.includes(s.id)));
              return (
                <div
                  key={service.id}
                  className={`flex flex-col overflow-hidden rounded-2xl ${
                    isSelected ? INVERSE : `${PANEL} ${INK}`
                  } ${blocked ? "opacity-50" : ""} transition-colors`}
                >
                  <button
                    type="button"
                    aria-pressed={isSelected}
                    disabled={blocked}
                    className={`flex flex-1 flex-col text-left focus-visible:outline-2 focus-visible:-outline-offset-2 ${PRESS}`}
                    onClick={() => onToggle(service.id)}
                  >
                    {service.image?.medium && (
                      <img
                        src={service.image.medium}
                        alt=""
                        className="aspect-[4/3] w-full object-cover"
                      />
                    )}
                    <span className="flex flex-1 flex-col gap-3 px-4 pt-3 pb-2">
                      <span className="flex items-start justify-between gap-2">
                        <span className="font-medium">{service.name}</span>
                        {isSelected && <CheckIcon />}
                      </span>
                      <span className="mt-auto flex items-baseline justify-between gap-2 text-sm">
                        <span className={isSelected ? "opacity-80" : MUTED}>
                          {t("booking.wizard.min", { count: service.duration_min })}
                        </span>
                        <span className="font-medium tabular-nums">{money(service.price)}</span>
                      </span>
                    </span>
                  </button>
                  <button
                    type="button"
                    className={`self-start px-4 pt-1 pb-3 text-sm underline underline-offset-4 focus-visible:outline-2 ${
                      isSelected ? "opacity-80" : MUTED
                    } hover:opacity-100`}
                    aria-label={t("booking.wizard.detailOf", { name: service.name })}
                    onClick={() => setDetail(service)}
                  >
                    {t("booking.wizard.detail")}
                  </button>
                </div>
              );
            })}
          </div>
        </section>
      ))}
      {detail && (
        <ServiceDetail
          service={detail}
          price={money(detail.price)}
          selected={selected.includes(detail.id)}
          canAdd={selected.length < MAX_SERVICES}
          onToggle={() => onToggle(detail.id)}
          onClose={() => setDetail(null)}
        />
      )}
    </div>
  );
}

// --- Paso 2a: profesional -----------------------------------------------------------------------

function Radio({ on }: { on: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={`flex size-6 shrink-0 items-center justify-center rounded-full border-2 ${
        on ? "border-[var(--color-primary)]" : "border-[var(--bk-line)]"
      }`}
    >
      {on && <span className="size-2.5 rounded-full bg-[var(--color-primary)]" />}
    </span>
  );
}

function ProfessionalRow({
  selected,
  onClick,
  avatar,
  name,
  sub,
}: {
  selected: boolean;
  onClick: () => void;
  avatar: ReactNode;
  name: string;
  sub?: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`flex min-h-16 w-full items-center gap-3 rounded-2xl px-4 py-3 text-left focus-visible:outline-2 ${PRESS} ${
        selected
          ? `${RAISED} ring-1 ring-[var(--color-primary)]`
          : `${PANEL} hover:bg-[var(--bk-raised)]`
      }`}
    >
      {avatar}
      <span className="min-w-0 flex-1">
        <span className="block font-medium">{name}</span>
        {sub}
      </span>
      <Radio on={selected} />
    </button>
  );
}

// Íconos dibujados con el color del texto, en vez de caracteres que algunos teléfonos pintan como emoji.
function CheckIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" className="mt-0.5 size-5 shrink-0" fill="none">
      <path
        d="M4 10.5l4 4 8-9"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function AnyoneIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="size-6" fill="none">
      <circle cx="9" cy="8" r="3.2" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="16.5" cy="9" r="2.6" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M3.5 19c.6-3.2 2.8-5 5.5-5s4.9 1.8 5.5 5M14.5 14.3c.6-.2 1.3-.3 2-.3 2.3 0 4 1.5 4.5 4.3"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function Initial({ letter, on }: { letter: ReactNode; on: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={`font-display flex size-11 shrink-0 items-center justify-center rounded-full text-lg ${
        on ? ACCENT : RAISED
      }`}
    >
      {letter}
    </span>
  );
}

function ProfessionalStep({
  professionals,
  selected,
  onSelect,
}: {
  professionals: PublicProfessional[];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const { t } = useTranslation();
  if (professionals.length === 0) {
    return <EmptyState>{t("booking.wizard.noProfessionals")}</EmptyState>;
  }
  return (
    <div className="flex flex-col gap-2">
      <ProfessionalRow
        selected={selected === ANY}
        onClick={() => onSelect(ANY)}
        avatar={<Initial letter={<AnyoneIcon />} on={selected === ANY} />}
        name={t("booking.wizard.anyone")}
        sub={<span className={`block text-sm ${MUTED}`}>{t("booking.wizard.anyoneHint")}</span>}
      />
      {professionals.map((professional) => {
        const on = selected === professional.id;
        const specialties = professional.specialties?.map((s) => s.name) ?? [];
        return (
          <ProfessionalRow
            key={professional.id}
            selected={on}
            onClick={() => onSelect(professional.id)}
            avatar={
              professional.photo?.thumb ? (
                <img
                  src={professional.photo.thumb}
                  alt=""
                  className="size-11 shrink-0 rounded-full object-cover"
                />
              ) : (
                <Initial letter={professional.display_name.charAt(0).toUpperCase()} on={on} />
              )
            }
            name={professional.display_name}
            sub={
              specialties.length > 0 ? (
                <span className={`block truncate text-sm ${MUTED}`}>
                  <span className="sr-only">{t("booking.wizard.specialties")}: </span>
                  {specialties.join(" · ")}
                </span>
              ) : professional.bio ? (
                <span className={`block truncate text-sm ${MUTED}`}>{professional.bio}</span>
              ) : undefined
            }
          />
        );
      })}
    </div>
  );
}

// --- Paso 2b: fecha ------------------------------------------------------------------------------

function DateStep({
  serviceIds,
  professionalId,
  selected,
  onSelect,
}: {
  serviceIds: string[];
  professionalId: string | null;
  selected: string;
  onSelect: (date: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const { timeZone } = useCompanyFormat();
  const today = todayIn(timeZone);
  const [month, setMonth] = useState(() => monthOf(selected || today));
  const days = useAvailableDays(serviceIds, professionalId, month);
  const statuses = dayStatuses(days.data);
  const monthLabel = new Intl.DateTimeFormat(i18n.language, {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${month}-15T12:00:00Z`));
  const weekdays = Array.from({ length: 7 }, (_, i) =>
    new Intl.DateTimeFormat(i18n.language, { weekday: "narrow", timeZone: "UTC" }).format(
      new Date(Date.UTC(2026, 10, 2 + i, 12)), // 2 nov 2026 es lunes
    ),
  );
  const arrow = `flex size-10 items-center justify-center rounded-full text-xl ${PANEL} disabled:opacity-40 focus-visible:outline-2 ${PRESS}`;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <p className="font-medium first-letter:uppercase" aria-live="polite">
          {monthLabel}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            className={arrow}
            aria-label={t("booking.wizard.prevMonth")}
            disabled={month <= monthOf(today)}
            onClick={() => setMonth((m) => addMonths(m, -1))}
          >
            ‹
          </button>
          <button
            type="button"
            className={arrow}
            aria-label={t("booking.wizard.nextMonth")}
            onClick={() => setMonth((m) => addMonths(m, 1))}
          >
            ›
          </button>
        </div>
      </div>
      {days.isError && (
        <ErrorBox message={describeError(t, days.error)} onRetry={() => void days.refetch()} />
      )}
      <div className="grid grid-cols-7 gap-1.5 text-center" role="grid" aria-busy={days.isPending}>
        {weekdays.map((name, index) => (
          <span key={`${name}-${index}`} className={`py-1 text-xs font-medium ${MUTED}`}>
            {name}
          </span>
        ))}
        {calendarCells(month).map((date, index) => {
          if (!date) return <span key={`empty-${index}`} />;
          const status = statuses.get(date) ?? "unavailable";
          return (
            <button
              key={date}
              type="button"
              disabled={status !== "available"}
              aria-pressed={selected === date}
              aria-label={t("booking.wizard.dayLabel", {
                day: formatDay(date, i18n.language),
                status: t(`booking.wizard.dayStatus.${status}`),
              })}
              onClick={() => onSelect(date)}
              className={`aspect-square rounded-xl text-sm font-medium tabular-nums focus-visible:outline-2 ${PRESS} ${
                selected === date ? ACCENT : DAY_STYLES[status]
              }`}
            >
              {Number(date.slice(8))}
            </button>
          );
        })}
      </div>
      {days.isSuccess && (
        <ul
          aria-label={t("booking.wizard.legend")}
          className={`flex flex-wrap gap-x-5 gap-y-1 text-sm ${MUTED}`}
        >
          {(["available", "full", "closed"] as const).map((status) => (
            <li key={status} className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className={`flex size-6 items-center justify-center rounded-md text-xs ${DAY_STYLES[status]}`}
              >
                1
              </span>
              {t(`booking.wizard.dayStatus.${status}`)}
            </li>
          ))}
        </ul>
      )}
      {days.isSuccess && days.data.days.length === 0 && (
        <Notice tone="info">{t("booking.wizard.noDaysThisMonth")}</Notice>
      )}
    </div>
  );
}

// --- Paso 2c: hora -------------------------------------------------------------------------------

function TimeStep({
  serviceIds,
  professionalId,
  date,
  selected,
  onSelect,
}: {
  serviceIds: string[];
  professionalId: string | null;
  date: string;
  selected: string;
  onSelect: (start: string) => void;
}) {
  const { t } = useTranslation();
  const { time } = useCompanyFormat();
  const slots = useSlots(serviceIds, professionalId, date);
  const [period, setPeriod] = useState<(typeof PERIODS)[number] | null>(null);
  if (slots.isPending) return <Loading />;
  if (slots.isError) {
    return (
      <ErrorBox message={describeError(t, slots.error)} onRetry={() => void slots.refetch()} />
    );
  }
  if (slots.data.length === 0) return <EmptyState>{t("booking.wizard.noSlots")}</EmptyState>;
  const groups = slotsByPeriod(slots.data);
  const periods = PERIODS.filter((p) => groups[p].length > 0);
  const chosenPeriod = periods.find((p) => groups[p].some((s) => s.start === selected));
  const active = period && periods.includes(period) ? period : (chosenPeriod ?? periods[0]);

  return (
    <div className="flex flex-col gap-4">
      <div role="tablist" aria-label={t("booking.wizard.steps.time")} className="flex gap-2">
        {periods.map((p) => (
          <button
            key={p}
            type="button"
            role="tab"
            aria-selected={p === active}
            onClick={() => setPeriod(p)}
            className={`min-h-10 rounded-full px-4 text-sm font-medium focus-visible:outline-2 ${PRESS} ${
              p === active ? INVERSE : `ring-1 ring-[var(--bk-line)] ring-inset ${MUTED}`
            }`}
          >
            {t(`booking.wizard.periods.${p}`)}
          </button>
        ))}
      </div>
      <div role="tabpanel" className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        {groups[active].map((slot) => (
          <button
            key={slot.start}
            type="button"
            aria-pressed={selected === slot.start}
            onClick={() => onSelect(slot.start)}
            className={`min-h-12 rounded-xl text-sm font-medium tabular-nums focus-visible:outline-2 ${PRESS} ${
              selected === slot.start ? ACCENT : `${PANEL} ${INK}`
            }`}
          >
            {time(slot.start)}
          </button>
        ))}
      </div>
    </div>
  );
}

// --- Paso 3: datos y confirmación ---------------------------------------------------------------

type FieldErrors = Partial<Record<keyof Customer | "accept", string>>;

function DetailsStep({
  customer,
  onCustomer,
  accept,
  onAccept,
  marketing,
  onMarketing,
  honeypot,
  onHoneypot,
  errors,
}: {
  customer: Customer;
  onCustomer: (customer: Customer) => void;
  accept: boolean;
  onAccept: (value: boolean) => void;
  marketing: boolean;
  onMarketing: (value: boolean) => void;
  honeypot: string;
  onHoneypot: (value: string) => void;
  errors: FieldErrors;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-4">
      <TextField
        label={t("booking.wizard.fullName")}
        autoComplete="name"
        className="min-h-12 text-base"
        value={customer.full_name}
        error={errors.full_name}
        onChange={(e) => onCustomer({ ...customer, full_name: e.target.value })}
      />
      <TextField
        label={t("booking.wizard.phone")}
        hint={t("booking.wizard.phoneHint")}
        type="tel"
        inputMode="tel"
        autoComplete="tel"
        className="min-h-12 text-base"
        value={customer.phone}
        error={errors.phone}
        onChange={(e) => onCustomer({ ...customer, phone: e.target.value })}
      />
      <TextField
        label={t("booking.wizard.email")}
        type="email"
        autoComplete="email"
        optional
        className="min-h-12 text-base"
        value={customer.email}
        error={errors.email}
        onChange={(e) => onCustomer({ ...customer, email: e.target.value })}
      />
      {/* Honeypot: invisible para las personas; si llega con texto, el servidor rechaza. */}
      <div aria-hidden="true" className="absolute -left-[9999px] h-0 overflow-hidden">
        <label>
          Website
          <input
            tabIndex={-1}
            autoComplete="off"
            value={honeypot}
            onChange={(e) => onHoneypot(e.target.value)}
          />
        </label>
      </div>
      <div className={`flex flex-col gap-1 rounded-2xl ${PANEL} p-4`}>
        <CheckboxField
          label={t("booking.wizard.acceptPolicy")}
          checked={accept}
          onChange={(e) => onAccept(e.target.checked)}
        />
        <Link
          to="/privacidad"
          target="_blank"
          className={`ml-8 text-sm underline underline-offset-4 ${MUTED}`}
        >
          {t("booking.wizard.readPolicy")}
        </Link>
        {errors.accept && (
          <p role="alert" className="ml-8 text-sm font-medium">
            {errors.accept}
          </p>
        )}
      </div>
      <div className={`rounded-2xl ${PANEL} p-4`}>
        <CheckboxField
          label={t("booking.wizard.marketing")}
          hint={t("booking.wizard.marketingHint")}
          checked={marketing}
          onChange={(e) => onMarketing(e.target.checked)}
        />
      </div>
    </div>
  );
}

// --- Asistente ----------------------------------------------------------------------------------

function slotTakenSuggestions(error: unknown): string[] {
  if (error instanceof ApiError && error.code === "slot_taken") {
    return ((error.fields as unknown as { suggestions?: string[] }).suggestions ?? []).slice(0, 6);
  }
  return [];
}

/** Errores de campo que manda el servidor para el cliente (`fields.customer.phone`, etc.). */
function serverFieldErrors(error: unknown): FieldErrors {
  if (!(error instanceof ApiError)) return {};
  const fields = error.fields as unknown as Record<string, unknown>;
  const nested = (fields.customer ?? {}) as Record<string, string[]>;
  const result: FieldErrors = {};
  for (const key of ["full_name", "phone", "email"] as const) {
    const messages = nested[key] ?? (fields[key] as string[] | undefined);
    if (messages?.length) result[key] = messages.join(" ");
  }
  return result;
}

/** Id del título de la reserva: la ventana (R9) lo usa como su nombre accesible. */
export const BOOKING_TITLE_ID = "booking-title";

export default function BookPage() {
  const { t, i18n } = useTranslation();
  const company = usePublicCompany().data;
  const services = usePublicServices();
  const { money, time, timeZone } = useCompanyFormat();
  const heading = useRef<HTMLHeadingElement>(null);
  const timeSection = useRef<HTMLElement>(null);

  const [step, setStep] = useState<Step>("services");
  const [serviceIds, setServiceIds] = useState<string[]>([]);
  const [professional, setProfessional] = useState<string | null>(null);
  const [date, setDate] = useState("");
  const [start, setStart] = useState("");
  const [customer, setCustomer] = useState<Customer>({ full_name: "", phone: "", email: "" });
  const [accept, setAccept] = useState(false);
  const [marketing, setMarketing] = useState(false);
  const [honeypot, setHoneypot] = useState("");
  // Cita para otra persona (su hijo, su papá): se pide su nombre; los datos de contacto son los
  // de quien reserva. Se activa con "Reservar otra cita para alguien más".
  const [forOther, setForOther] = useState(false);
  const [attendee, setAttendee] = useState("");
  // La cita recién reservada se puede cancelar desde la misma confirmación.
  const [cancelled, setCancelled] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});

  const professionals = usePublicProfessionals(serviceIds);
  const professionalId = professional === ANY ? null : professional;
  const chosen = selectedServices(services.data ?? [], serviceIds);
  const orderedIds = chosen.map((s) => s.id);
  const total = totals(chosen);

  const book = useMutation({
    mutationFn: () =>
      api<PublicBooked>("/api/v1/public/appointments/", {
        method: "POST",
        body: bookingPayload({
          serviceIds: orderedIds,
          professionalId,
          start,
          customer,
          acceptDataPolicy: accept,
          marketingConsent: marketing,
          website: honeypot,
          attendeeName: forOther ? attendee : "",
        }),
      }),
    onError: (error) => setErrors(serverFieldErrors(error)),
  });

  const stepIndex = STEPS.indexOf(step);
  // Al cambiar de paso, el foco va al título: así lo anuncia un lector de pantalla. Dentro de la
  // ventana (R9) además se vuelve arriba, para ver el número de paso.
  useEffect(() => {
    const element = heading.current;
    element?.focus({ preventScroll: true });
    element?.closest("dialog")?.scrollTo?.({ top: 0 });
  }, [step, book.isSuccess]);
  // Con profesional, día y hora en la misma vista, al elegir el día se baja a las horas.
  useEffect(() => {
    if (date) timeSection.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }, [date]);

  if (company && !company.booking_enabled) {
    return <Notice tone="warning">{t("booking.disabled")}</Notice>;
  }
  if (services.isPending) return <Loading />;
  if (services.isError) {
    return (
      <ErrorBox
        message={describeError(t, services.error)}
        onRetry={() => void services.refetch()}
      />
    );
  }

  /** Nueva cita para otra persona, con los datos de contacto ya llenos. */
  function bookAnother() {
    book.reset();
    setServiceIds([]);
    setProfessional(null);
    setDate("");
    setStart("");
    setErrors({});
    setAttendee("");
    setCancelled(false);
    setForOther(true);
    setStep("services");
  }

  if (book.isSuccess) {
    const manageUrl = new URL(book.data.manage_url, window.location.origin).pathname;
    return (
      <div className="flex flex-col gap-5 pb-6">
        <h1
          id={BOOKING_TITLE_ID}
          ref={heading}
          tabIndex={-1}
          className="font-display text-3xl leading-tight outline-none"
        >
          {cancelled ? t("booking.manage.cancelled") : t("booking.wizard.done")}
        </h1>
        {!cancelled && <p className={MUTED}>{t("booking.wizard.doneHint")}</p>}
        <div className={`rounded-2xl ${PANEL} p-5 ${cancelled ? "opacity-60" : ""}`}>
          <AppointmentSummary appointment={book.data} />
        </div>
        {!cancelled && (
          <>
            <Link
              to={manageUrl}
              className={`inline-flex min-h-14 items-center justify-center rounded-2xl px-4 font-semibold ${ACCENT} ${PRESS}`}
            >
              {t("booking.wizard.manageLink")}
            </Link>
            <p className={`text-sm ${MUTED}`}>{t("booking.wizard.saveLink")}</p>
            <CancelAppointment
              token={tokenFromManageUrl(manageUrl)}
              canCancel={book.data.can_cancel}
              deadline={book.data.cancel_deadline}
              onCancelled={() => setCancelled(true)}
            />
          </>
        )}
        <button
          type="button"
          onClick={bookAnother}
          className={`min-h-14 rounded-2xl px-4 font-medium ${PANEL} ${INK} focus-visible:outline-2 ${PRESS}`}
        >
          {t("booking.wizard.anotherBooking")}
        </button>
      </div>
    );
  }

  const canContinue =
    (step === "services" && serviceIds.length > 0 && (!forOther || attendee.trim() !== "")) ||
    (step === "schedule" && Boolean(start));

  function go(next: Step) {
    book.reset();
    setStep(next);
  }

  function submit() {
    const found: FieldErrors = {};
    if (!customer.full_name.trim()) found.full_name = t("common.required");
    if (!looksLikePhone(customer.phone)) found.phone = t("booking.wizard.phoneInvalid");
    if (customer.email.trim() && !/^\S+@\S+\.\S+$/.test(customer.email.trim())) {
      found.email = t("common.emailFormat");
    }
    if (!accept) found.accept = t("booking.wizard.acceptRequired");
    setErrors(found);
    if (Object.keys(found).length === 0) book.mutate();
  }

  const suggestions = slotTakenSuggestions(book.error);
  const professionalName =
    professional === ANY
      ? t("booking.wizard.anyone")
      : (professionals.data?.find((p) => p.id === professional)?.display_name ?? "");
  const shortDay = (iso: string) =>
    new Intl.DateTimeFormat(i18n.language, {
      weekday: "short",
      day: "numeric",
      month: "short",
      timeZone,
    }).format(new Date(iso));
  const when = start
    ? `${shortDay(start)} · ${time(start)}`
    : date
      ? formatDay(date, i18n.language)
      : "";
  const ctaLabel =
    step === "services"
      ? t("booking.wizard.continue")
      : step === "schedule"
        ? start
          ? t("booking.wizard.continueAt", { time: time(start) })
          : t("booking.wizard.pickTime")
        : book.isPending
          ? t("booking.wizard.booking")
          : t("booking.wizard.confirmAt", { time: time(start) });

  return (
    // Ocupa toda la altura de la ventana: la barra de botones queda abajo aunque haya poco contenido.
    <div className="flex flex-1 flex-col gap-6 tabular-nums">
      <Ticket
        services={chosen.map((s) => s.name).join(" + ")}
        forName={forOther ? attendee.trim() : ""}
        who={step === "services" ? "" : professionalName}
        when={step === "services" ? "" : when}
        minutes={total.minutes}
        price={money(total.price)}
        note={step === "details" ? t("booking.summary.priceMayVary") : undefined}
      />

      <div className="flex flex-col gap-3">
        <div className="flex gap-1.5" aria-hidden="true">
          {STEPS.map((name, index) => (
            <span
              key={name}
              className={`h-1 flex-1 rounded-full ${
                index <= stepIndex ? "bg-[var(--color-primary)]" : "bg-[var(--bk-raised)]"
              }`}
            />
          ))}
        </div>
        <p className={`text-sm ${MUTED}`}>
          {t("booking.wizard.stepOf", { step: stepIndex + 1, total: STEPS.length })}
        </p>
        <h1
          id={BOOKING_TITLE_ID}
          ref={heading}
          tabIndex={-1}
          className="font-display text-3xl leading-tight outline-none"
        >
          {t(`booking.wizard.steps.${step}`)}
        </h1>
      </div>

      {step === "services" && forOther && (
        <section
          aria-labelledby="booking-who"
          className={`flex flex-col gap-3 rounded-2xl ${PANEL} p-4`}
        >
          <h2 id="booking-who" className="font-display text-xl leading-tight">
            {t("booking.wizard.whoTitle")}
          </h2>
          <TextField
            label={t("booking.wizard.whoLabel")}
            hint={t("booking.wizard.whoHint")}
            autoComplete="off"
            className="min-h-12 text-base"
            value={attendee}
            onChange={(e) => setAttendee(e.target.value)}
          />
          <button
            type="button"
            onClick={() => {
              setForOther(false);
              setAttendee("");
            }}
            className={`self-start text-sm underline underline-offset-4 ${MUTED} focus-visible:outline-2`}
          >
            {t("booking.wizard.forMe")}
          </button>
        </section>
      )}
      {step === "services" && (
        <ServicesStep
          categories={services.data}
          selected={serviceIds}
          onToggle={(id) => {
            setServiceIds((ids) => toggleService(services.data ?? [], ids, id));
            // Otros servicios cambian quién atiende y qué horarios hay: se vuelven a elegir.
            setProfessional(null);
            setDate("");
            setStart("");
          }}
        />
      )}
      {step === "schedule" && (
        <div className="flex flex-col gap-10">
          <section className="flex flex-col gap-3" aria-labelledby="schedule-professional">
            <h2 id="schedule-professional" className={SECTION_TITLE}>
              {t("booking.wizard.steps.professional")}
            </h2>
            {professionals.isPending ? (
              <Loading />
            ) : professionals.isError ? (
              <ErrorBox
                message={describeError(t, professionals.error)}
                onRetry={() => void professionals.refetch()}
              />
            ) : (
              <ProfessionalStep
                professionals={professionals.data}
                selected={professional}
                onSelect={(id) => {
                  setProfessional(id);
                  setDate("");
                  setStart("");
                }}
              />
            )}
          </section>
          {professional !== null && (
            <section className="flex flex-col gap-3" aria-labelledby="schedule-date">
              <h2 id="schedule-date" className={SECTION_TITLE}>
                {t("booking.wizard.steps.date")}
              </h2>
              <DateStep
                serviceIds={orderedIds}
                professionalId={professionalId}
                selected={date}
                onSelect={(value) => {
                  setDate(value);
                  setStart("");
                }}
              />
            </section>
          )}
          {professional !== null && date && (
            <section
              ref={timeSection}
              className="flex scroll-mt-44 flex-col gap-3"
              aria-labelledby="schedule-time"
            >
              <h2 id="schedule-time" className={`${SECTION_TITLE} first-letter:uppercase`}>
                {formatDay(date, i18n.language)}
              </h2>
              <TimeStep
                serviceIds={orderedIds}
                professionalId={professionalId}
                date={date}
                selected={start}
                onSelect={setStart}
              />
            </section>
          )}
        </div>
      )}
      {step === "details" && (
        <DetailsStep
          customer={customer}
          onCustomer={setCustomer}
          accept={accept}
          onAccept={setAccept}
          marketing={marketing}
          onMarketing={setMarketing}
          honeypot={honeypot}
          onHoneypot={setHoneypot}
          errors={errors}
        />
      )}

      {book.isError && (
        <Notice tone="danger">
          {describeError(t, book.error)}
          {suggestions.length > 0 && (
            <span className="mt-3 flex flex-wrap gap-2">
              {suggestions.map((iso) => (
                <button
                  key={iso}
                  type="button"
                  className="min-h-10 rounded-full bg-white px-4 text-sm font-medium text-slate-900 ring-1 ring-slate-300"
                  onClick={() => {
                    setStart(iso);
                    book.reset();
                  }}
                >
                  {time(iso)}
                </button>
              ))}
            </span>
          )}
        </Notice>
      )}

      {/* Barra fija abajo en el celular: el botón principal siempre a mano. */}
      <div className="sticky bottom-0 -mx-4 mt-auto flex gap-2 bg-[var(--color-background)] px-4 pt-2 pb-4">
        {stepIndex > 0 && (
          <button
            type="button"
            onClick={() => go(STEPS[stepIndex - 1])}
            className={`min-h-14 rounded-2xl px-5 font-medium ${PANEL} ${INK} focus-visible:outline-2 ${PRESS}`}
          >
            {t("common.back")}
          </button>
        )}
        <button
          type="button"
          disabled={step === "details" ? book.isPending : !canContinue}
          onClick={step === "details" ? submit : () => go(STEPS[stepIndex + 1])}
          className={`min-h-14 flex-1 rounded-2xl px-4 font-semibold focus-visible:outline-2 ${PRESS} ${ACCENT} disabled:cursor-not-allowed disabled:bg-[var(--bk-raised)] disabled:text-[var(--bk-muted)]`}
        >
          {ctaLabel} <span aria-hidden="true">→</span>
        </button>
      </div>
    </div>
  );
}
