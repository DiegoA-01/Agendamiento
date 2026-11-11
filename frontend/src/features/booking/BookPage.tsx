import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
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
  Button,
  Card,
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
  totals,
  type Customer,
  type Step,
} from "./wizard";

const ANY = "any";
const OPTION =
  "flex w-full items-center gap-3 rounded-xl border-2 p-3 text-left transition-colors focus-visible:outline-2";
const optionStyle = (selected: boolean) =>
  `${OPTION} ${
    selected
      ? "border-[var(--color-primary,#0f172a)] bg-[var(--color-surface,#ffffff)]"
      : "border-black/10 bg-[var(--color-surface,#ffffff)] hover:border-black/30"
  }`;

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
    <div className="flex flex-col gap-5">
      {categories.map((category) => (
        <section key={category.id} className="flex flex-col gap-2">
          <h2 className="font-semibold">{category.name}</h2>
          {category.services.map((service) => {
            const isSelected = selected.includes(service.id);
            return (
              <div key={service.id} className="flex items-stretch gap-2">
                <button
                  type="button"
                  aria-pressed={isSelected}
                  disabled={!isSelected && selected.length >= MAX_SERVICES}
                  className={optionStyle(isSelected)}
                  onClick={() => onToggle(service.id)}
                >
                  {service.image?.thumb && (
                    <img
                      src={service.image.thumb}
                      alt=""
                      className="size-14 rounded-lg object-cover"
                    />
                  )}
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium">{service.name}</span>
                    <span className="block text-sm opacity-80">
                      {money(service.price)} ·{" "}
                      {t("catalog.services.minutes", { count: service.duration_min })}
                    </span>
                    {service.description && (
                      <span className="mt-1 line-clamp-2 block text-sm opacity-70">
                        {service.description}
                      </span>
                    )}
                  </span>
                  <span aria-hidden="true" className="text-xl">
                    {isSelected ? "✓" : "+"}
                  </span>
                </button>
                <button
                  type="button"
                  className="shrink-0 rounded-xl border-2 border-black/10 bg-[var(--color-surface,#ffffff)] px-3 text-sm font-medium hover:border-black/30 focus-visible:outline-2"
                  aria-label={t("booking.wizard.detailOf", { name: service.name })}
                  onClick={() => setDetail(service)}
                >
                  {t("booking.wizard.detail")}
                </button>
              </div>
            );
          })}
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

// --- Paso 2: profesional ------------------------------------------------------------------------

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
      <button
        type="button"
        aria-pressed={selected === ANY}
        className={optionStyle(selected === ANY)}
        onClick={() => onSelect(ANY)}
      >
        <span className="flex size-12 items-center justify-center rounded-full bg-black/10 text-xl">
          ★
        </span>
        <span>
          <span className="block font-medium">{t("booking.wizard.anyone")}</span>
          <span className="block text-sm opacity-80">{t("booking.wizard.anyoneHint")}</span>
        </span>
      </button>
      {professionals.map((professional) => (
        <button
          key={professional.id}
          type="button"
          aria-pressed={selected === professional.id}
          className={optionStyle(selected === professional.id)}
          onClick={() => onSelect(professional.id)}
        >
          {professional.photo?.thumb ? (
            <img
              src={professional.photo.thumb}
              alt=""
              className="size-12 rounded-full object-cover"
            />
          ) : (
            <span
              aria-hidden="true"
              className="flex size-12 items-center justify-center rounded-full bg-black/10 font-semibold"
            >
              {professional.display_name.charAt(0).toUpperCase()}
            </span>
          )}
          <span className="min-w-0">
            <span className="block font-medium">{professional.display_name}</span>
            {professional.bio && (
              <span className="block truncate text-sm opacity-80">{professional.bio}</span>
            )}
            {professional.specialties?.length > 0 && (
              <span className="mt-1 flex flex-wrap gap-1">
                <span className="sr-only">{t("booking.wizard.specialties")}:</span>
                {professional.specialties.map((specialty) => (
                  <span
                    key={specialty.id}
                    className="rounded-full bg-black/5 px-2 py-0.5 text-xs font-medium"
                  >
                    {specialty.name}
                  </span>
                ))}
              </span>
            )}
          </span>
        </button>
      ))}
    </div>
  );
}

// --- Paso 3: fecha ------------------------------------------------------------------------------

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
    new Intl.DateTimeFormat(i18n.language, { weekday: "short", timeZone: "UTC" }).format(
      new Date(Date.UTC(2026, 10, 2 + i, 12)), // 2 nov 2026 es lunes
    ),
  );

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <Button
          variant="ghost"
          aria-label={t("booking.wizard.prevMonth")}
          disabled={month <= monthOf(today)}
          onClick={() => setMonth((m) => addMonths(m, -1))}
        >
          ‹
        </Button>
        <h2 className="font-semibold first-letter:uppercase" aria-live="polite">
          {monthLabel}
        </h2>
        <Button
          variant="ghost"
          aria-label={t("booking.wizard.nextMonth")}
          onClick={() => setMonth((m) => addMonths(m, 1))}
        >
          ›
        </Button>
      </div>
      {days.isError && (
        <ErrorBox message={describeError(t, days.error)} onRetry={() => void days.refetch()} />
      )}
      <div className="grid grid-cols-7 gap-1 text-center" role="grid" aria-busy={days.isPending}>
        {weekdays.map((name) => (
          <span key={name} className="py-1 text-xs font-medium uppercase opacity-70">
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
              className={`aspect-square rounded-lg text-sm font-medium ${
                selected === date ? "bg-slate-900 text-white" : DAY_STYLES[status]
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
          className="flex flex-wrap justify-center gap-x-4 gap-y-1 text-xs"
        >
          {(["available", "full", "closed"] as const).map((status) => (
            <li key={status} className="flex items-center gap-1.5">
              <span
                aria-hidden="true"
                className={`size-3 rounded border border-slate-400/60 ${DAY_STYLES[status]}`}
              />
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

// --- Paso 4: hora -------------------------------------------------------------------------------

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
  const { t, i18n } = useTranslation();
  const { time } = useCompanyFormat();
  const slots = useSlots(serviceIds, professionalId, date);
  if (slots.isPending) return <Loading />;
  if (slots.isError) {
    return (
      <ErrorBox message={describeError(t, slots.error)} onRetry={() => void slots.refetch()} />
    );
  }
  if (slots.data.length === 0) return <EmptyState>{t("booking.wizard.noSlots")}</EmptyState>;
  const groups = slotsByPeriod(slots.data);

  return (
    <div className="flex flex-col gap-5">
      <p className="font-medium first-letter:uppercase">{formatDay(date, i18n.language)}</p>
      {PERIODS.filter((period) => groups[period].length > 0).map((period) => (
        <section key={period} className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold uppercase opacity-70">
            {t(`booking.wizard.periods.${period}`)}
          </h2>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
            {groups[period].map((slot) => (
              <button
                key={slot.start}
                type="button"
                aria-pressed={selected === slot.start}
                onClick={() => onSelect(slot.start)}
                className={`min-h-11 rounded-lg border text-sm font-medium ${
                  selected === slot.start
                    ? "border-slate-900 bg-slate-900 text-white"
                    : "border-black/15 bg-[var(--color-surface,#ffffff)] hover:border-black/40"
                }`}
              >
                {time(slot.start)}
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

// --- Paso 5: datos y confirmación ---------------------------------------------------------------

type FieldErrors = Partial<Record<keyof Customer | "accept", string>>;

function DetailsStep({
  summary,
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
  summary: { services: string; when: string; with: string; total: string };
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
    <div className="flex flex-col gap-5">
      <Card className="!bg-[var(--color-surface,#ffffff)]">
        <dl className="grid gap-2 text-sm sm:grid-cols-[auto_1fr] sm:gap-x-6">
          <dt className="opacity-70">{t("booking.summary.services")}</dt>
          <dd className="font-medium">{summary.services}</dd>
          <dt className="opacity-70">{t("booking.summary.when")}</dt>
          <dd className="font-medium first-letter:uppercase">{summary.when}</dd>
          <dt className="opacity-70">{t("booking.summary.with")}</dt>
          <dd>{summary.with}</dd>
          <dt className="opacity-70">{t("booking.summary.referencePrice")}</dt>
          <dd className="font-semibold">{summary.total}</dd>
        </dl>
        <p className="mt-3 text-xs opacity-70">{t("booking.summary.priceMayVary")}</p>
      </Card>
      <div className="flex flex-col gap-4">
        <TextField
          label={t("booking.wizard.fullName")}
          autoComplete="name"
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
          value={customer.phone}
          error={errors.phone}
          onChange={(e) => onCustomer({ ...customer, phone: e.target.value })}
        />
        <TextField
          label={t("booking.wizard.email")}
          type="email"
          autoComplete="email"
          optional
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
        <div className="flex flex-col gap-1">
          <CheckboxField
            label={t("booking.wizard.acceptPolicy")}
            checked={accept}
            onChange={(e) => onAccept(e.target.checked)}
          />
          <Link to="/privacidad" target="_blank" className="ml-8 text-sm underline">
            {t("booking.wizard.readPolicy")}
          </Link>
          {errors.accept && (
            <p role="alert" className="ml-8 text-xs font-medium text-red-700">
              {errors.accept}
            </p>
          )}
        </div>
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

export default function BookPage() {
  const { t, i18n } = useTranslation();
  const company = usePublicCompany().data;
  const services = usePublicServices();
  const { money, time, timeZone } = useCompanyFormat();
  const heading = useRef<HTMLHeadingElement>(null);

  const [step, setStep] = useState<Step>("services");
  const [serviceIds, setServiceIds] = useState<string[]>([]);
  const [professional, setProfessional] = useState<string | null>(null);
  const [date, setDate] = useState("");
  const [start, setStart] = useState("");
  const [customer, setCustomer] = useState<Customer>({ full_name: "", phone: "", email: "" });
  const [accept, setAccept] = useState(false);
  const [marketing, setMarketing] = useState(false);
  const [honeypot, setHoneypot] = useState("");
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
        }),
      }),
    onError: (error) => setErrors(serverFieldErrors(error)),
  });

  const stepIndex = STEPS.indexOf(step);
  // Al cambiar de paso, el foco va al título: así lo anuncia un lector de pantalla.
  useEffect(() => heading.current?.focus(), [step, book.isSuccess]);

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

  if (book.isSuccess) {
    const manageUrl = new URL(book.data.manage_url, window.location.origin).pathname;
    return (
      <div className="flex flex-col gap-5">
        <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold outline-none">
          {t("booking.wizard.done")}
        </h1>
        <Notice tone="success">{t("booking.wizard.doneHint")}</Notice>
        <Card className="!bg-[var(--color-surface,#ffffff)]">
          <AppointmentSummary appointment={book.data} />
        </Card>
        <Link
          to={manageUrl}
          className="inline-flex min-h-11 items-center justify-center rounded-lg bg-slate-900 px-4 font-medium text-white"
        >
          {t("booking.wizard.manageLink")}
        </Link>
        <p className="text-sm opacity-80">{t("booking.wizard.saveLink")}</p>
      </div>
    );
  }

  const canContinue =
    (step === "services" && serviceIds.length > 0) ||
    (step === "professional" && professional !== null) ||
    (step === "date" && Boolean(date)) ||
    (step === "time" && Boolean(start));

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

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium opacity-70">
          {t("booking.wizard.stepOf", { step: stepIndex + 1, total: STEPS.length })}
        </p>
        <div className="flex gap-1" aria-hidden="true">
          {STEPS.map((name, index) => (
            <span
              key={name}
              className={`h-1.5 flex-1 rounded-full ${
                index <= stepIndex ? "bg-[var(--color-primary,#0f172a)]" : "bg-black/10"
              }`}
            />
          ))}
        </div>
        <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold outline-none">
          {t(`booking.wizard.steps.${step}`)}
        </h1>
      </div>

      {step === "services" && (
        <ServicesStep
          categories={services.data}
          selected={serviceIds}
          onToggle={(id) => {
            setServiceIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]));
            // Otros servicios cambian quién atiende y qué horarios hay: se vuelven a elegir.
            setProfessional(null);
            setDate("");
            setStart("");
          }}
        />
      )}
      {step === "professional" &&
        (professionals.isPending ? (
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
        ))}
      {step === "date" && (
        <DateStep
          serviceIds={orderedIds}
          professionalId={professionalId}
          selected={date}
          onSelect={(value) => {
            setDate(value);
            setStart("");
          }}
        />
      )}
      {step === "time" && (
        <TimeStep
          serviceIds={orderedIds}
          professionalId={professionalId}
          date={date}
          selected={start}
          onSelect={setStart}
        />
      )}
      {step === "details" && (
        <DetailsStep
          summary={{
            services: chosen.map((s) => s.name).join(", "),
            when: `${new Intl.DateTimeFormat(i18n.language, { dateStyle: "full", timeZone }).format(new Date(start))}, ${time(start)}`,
            with: professionalName,
            total: money(total.price),
          }}
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
                <Button
                  key={iso}
                  variant="secondary"
                  onClick={() => {
                    setStart(iso);
                    book.reset();
                  }}
                >
                  {time(iso)}
                </Button>
              ))}
            </span>
          )}
        </Notice>
      )}

      {serviceIds.length > 0 && step === "services" && (
        <p className="text-sm opacity-80">
          {t("booking.wizard.selection", { count: serviceIds.length })} ·{" "}
          {t("catalog.services.minutes", { count: total.minutes })} · {money(total.price)}
        </p>
      )}

      {/* Barra fija abajo en el celular: el botón principal siempre a mano. */}
      <div className="sticky bottom-0 -mx-4 flex gap-2 border-t border-black/10 bg-[var(--color-background,#f8fafc)] px-4 py-3">
        {stepIndex > 0 && (
          <Button variant="secondary" onClick={() => go(STEPS[stepIndex - 1])}>
            {t("common.back")}
          </Button>
        )}
        {step !== "details" ? (
          <Button
            className="flex-1"
            disabled={!canContinue}
            onClick={() => go(STEPS[stepIndex + 1])}
          >
            {t("booking.wizard.continue")}
          </Button>
        ) : (
          <Button className="flex-1" disabled={book.isPending} onClick={submit}>
            {book.isPending ? t("booking.wizard.booking") : t("booking.wizard.confirm")}
          </Button>
        )}
      </div>
    </div>
  );
}
