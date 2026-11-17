import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ApiError, api } from "../../../shared/api/client";
import { describeError } from "../../../shared/api/errors";
import type {
  ConflictingAppointment,
  Paginated,
  Professional,
  TimeBlock,
  WorkingHours,
} from "../../../shared/api/types";
import {
  Button,
  Card,
  EmptyState,
  ErrorBox,
  Loading,
  Notice,
  PageHeader,
  SelectField,
  TextField,
} from "../../../shared/ui/primitives";
import { useMe } from "../../auth/useMe";
import { KEYS, useProfessionals } from "../shared/api";
import { useCan } from "../shared/useCan";
import {
  copyPlanDay,
  planFromWeek,
  planHasErrors,
  suggestBreak,
  validatePlan,
  weekFromPlan,
  type DayPlan,
  type Plan,
} from "./plan";
import { WEEKDAYS, hoursFromWeek, weekFromHours, weeklyMinutes, type Week } from "./week";

const WORKDAYS = [1, 2, 3, 4] as const; // martes a viernes, para "copiar el lunes"

function useTenantDateTime() {
  const { i18n } = useTranslation();
  const timeZone = useMe().data?.tenant?.timezone;
  return (iso: string) =>
    new Intl.DateTimeFormat(i18n.language, {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone,
    }).format(new Date(iso));
}

// --- Semana -------------------------------------------------------------------------------------

function WeekEditor({
  professional,
  initial,
  editable,
}: {
  professional: Professional;
  initial: Week;
  editable: boolean;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [plan, setPlan] = useState<Plan>(() => planFromWeek(initial));
  const [message, setMessage] = useState<{ tone: "success" | "danger"; text: string } | null>(null);
  const [showErrors, setShowErrors] = useState(false);
  const errors = validatePlan(plan);

  const save = useMutation({
    mutationFn: () =>
      api<WorkingHours[]>(`/api/v1/professionals/${professional.id}/working-hours/`, {
        method: "PUT",
        body: hoursFromWeek(weekFromPlan(plan)),
      }),
    onSuccess: (saved) => {
      queryClient.setQueryData(KEYS.workingHours(professional.id), saved);
      setPlan(planFromWeek(weekFromHours(saved)));
      setMessage({ tone: "success", text: t("common.saved") });
    },
    onError: (error) => setMessage({ tone: "danger", text: describeError(t, error) }),
  });

  function change(weekday: number, next: (day: DayPlan | null) => DayPlan | null) {
    setMessage(null);
    setPlan((current) => current.map((day, d) => (d === weekday ? next(day) : day)));
  }
  const setDay = (weekday: number, field: "start" | "end", value: string) =>
    change(weekday, (day) => day && { ...day, [field]: value });
  const setBreak = (weekday: number, index: number, field: "start" | "end", value: string) =>
    change(
      weekday,
      (day) =>
        day && {
          ...day,
          breaks: day.breaks.map((pause, i) =>
            i === index ? { ...pause, [field]: value } : pause,
          ),
        },
    );
  const addBreak = (weekday: number) =>
    change(weekday, (day) => day && { ...day, breaks: [...day.breaks, suggestBreak(day)] });
  const removeBreak = (weekday: number, index: number) =>
    change(weekday, (day) => day && { ...day, breaks: day.breaks.filter((_, i) => i !== index) });
  const toggleDay = (weekday: number, open: boolean) =>
    change(weekday, () => (open ? { start: "09:00", end: "18:00", breaks: [] } : null));

  const minutes = weeklyMinutes(weekFromPlan(plan));
  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{t("catalog.hours.week")}</h2>
          <p className="text-sm text-slate-600">
            {t("catalog.hours.weekTotal", {
              hours: Math.floor(minutes / 60),
              minutes: minutes % 60,
            })}
          </p>
        </div>
        {editable && plan[0] && (
          <Button variant="secondary" onClick={() => setPlan((p) => copyPlanDay(p, 0, WORKDAYS))}>
            {t("catalog.hours.copyMonday")}
          </Button>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-4 text-sm text-slate-600" aria-hidden="true">
        <span className="flex items-center gap-2">
          <span className="hours-work inline-block h-3 w-6 rounded-full" />
          {t("catalog.hours.legendWork")}
        </span>
        <span className="flex items-center gap-2">
          <span className="hours-break inline-block h-3 w-6 rounded-full" />
          {t("catalog.hours.legendBreak")}
        </span>
      </div>
      {message && <Notice tone={message.tone}>{message.text}</Notice>}
      <ul className="flex flex-col gap-2">
        {WEEKDAYS.map((weekday) => {
          const day = plan[weekday];
          const dayErrors = showErrors ? errors[weekday] : null;
          return (
            <li key={weekday} className="flex flex-col gap-3 py-4 lg:flex-row lg:items-start">
              <div className="flex w-36 shrink-0 items-center justify-between gap-2 pt-1 lg:flex-col lg:items-start">
                <span className="font-medium">{t(`catalog.hours.days.${weekday}`)}</span>
                {editable ? (
                  <label className="flex items-center gap-2 text-sm text-slate-600">
                    <input
                      type="checkbox"
                      checked={day !== null}
                      onChange={(e) => toggleDay(weekday, e.target.checked)}
                    />
                    {t("catalog.hours.works")}
                  </label>
                ) : (
                  !day && (
                    <span className="text-sm text-slate-500">{t("catalog.hours.closed")}</span>
                  )
                )}
              </div>

              {day ? (
                <div className="flex flex-1 flex-col gap-3">
                  <DayTrack day={day} />
                  <div className="flex flex-wrap items-end gap-2">
                    <span className="w-full text-sm font-medium text-slate-600">
                      {t("catalog.hours.workday")}
                    </span>
                    <div className="w-36">
                      <TextField
                        label={t("catalog.hours.from")}
                        type="time"
                        value={day.start}
                        disabled={!editable}
                        onChange={(e) => setDay(weekday, "start", e.target.value)}
                      />
                    </div>
                    <div className="w-36">
                      <TextField
                        label={t("catalog.hours.to")}
                        type="time"
                        value={day.end}
                        disabled={!editable}
                        error={dayErrors?.day ? `hours_${dayErrors.day}` : undefined}
                        onChange={(e) => setDay(weekday, "end", e.target.value)}
                      />
                    </div>
                  </div>

                  {day.breaks.map((pause, index) => {
                    const error = dayErrors?.breaks[index];
                    return (
                      <div
                        key={index}
                        className="hours-break-box flex flex-wrap items-end gap-2 rounded-2xl p-3"
                      >
                        <span className="flex w-full items-center gap-2 text-sm font-semibold">
                          <span className="hours-break inline-block size-3 rounded-full" />
                          {t("catalog.hours.breakTitle", { n: index + 1 })}
                        </span>
                        <div className="w-36">
                          <TextField
                            label={t("catalog.hours.breakFrom")}
                            type="time"
                            value={pause.start}
                            disabled={!editable}
                            onChange={(e) => setBreak(weekday, index, "start", e.target.value)}
                          />
                        </div>
                        <div className="w-36">
                          <TextField
                            label={t("catalog.hours.breakTo")}
                            type="time"
                            value={pause.end}
                            disabled={!editable}
                            error={error ? `hours_${error}` : undefined}
                            onChange={(e) => setBreak(weekday, index, "end", e.target.value)}
                          />
                        </div>
                        {editable && (
                          <Button
                            variant="dangerGhost"
                            aria-label={t("catalog.hours.removeBreak")}
                            onClick={() => removeBreak(weekday, index)}
                          >
                            {t("catalog.hours.remove")}
                          </Button>
                        )}
                      </div>
                    );
                  })}

                  {editable && (
                    <div>
                      <Button variant="secondary" onClick={() => addBreak(weekday)}>
                        + {t("catalog.hours.addBreakSlot")}
                      </Button>
                    </div>
                  )}
                </div>
              ) : (
                <p className="flex-1 pt-1 text-sm text-slate-500">{t("catalog.hours.closed")}</p>
              )}
            </li>
          );
        })}
      </ul>
      {editable && (
        <div>
          <Button
            disabled={save.isPending}
            onClick={() => {
              setShowErrors(true);
              if (!planHasErrors(errors)) save.mutate();
              else setMessage({ tone: "danger", text: t("errors.validation_error") });
            }}
          >
            {save.isPending ? t("common.saving") : t("catalog.hours.save")}
          </Button>
        </div>
      )}
    </Card>
  );
}

const minutesOf = (time: string) => Number(time.slice(0, 2)) * 60 + Number(time.slice(3, 5));

/** Barra del día de 6:00 a 22:00 (o más si la jornada se sale): la jornada en el color del panel
 *  y cada descanso en franjas ámbar encima, con su hora. */
function DayTrack({ day }: { day: DayPlan }) {
  const { t } = useTranslation();
  if (!day.start || !day.end || day.start >= day.end) return null;
  const from = Math.min(6 * 60, minutesOf(day.start));
  const to = Math.max(22 * 60, minutesOf(day.end));
  const pct = (time: string) => ((minutesOf(time) - from) / (to - from)) * 100;
  const segment = (start: string, end: string) => ({
    left: `${pct(start)}%`,
    width: `${Math.max(0, pct(end) - pct(start))}%`,
  });
  return (
    <div className="hours-track relative mb-5 h-8 rounded-full" aria-hidden="true">
      <span
        className="hours-work absolute inset-y-1 rounded-full"
        style={segment(day.start, day.end)}
      />
      {day.breaks
        .filter((pause) => pause.start && pause.end && pause.start < pause.end)
        .map((pause, index) => (
          <span
            key={index}
            className="hours-break absolute inset-y-0 flex items-center justify-center overflow-hidden rounded-full text-[11px] font-semibold"
            style={segment(pause.start, pause.end)}
            title={t("catalog.hours.breakRange", { start: pause.start, end: pause.end })}
          >
            {pause.start}
          </span>
        ))}
      <span
        className="absolute -bottom-5 text-[11px] text-slate-500"
        style={{ left: `${pct(day.start)}%` }}
      >
        {day.start}
      </span>
      <span
        className="absolute -bottom-5 -translate-x-full text-[11px] text-slate-500"
        style={{ left: `${pct(day.end)}%` }}
      >
        {day.end}
      </span>
    </div>
  );
}

function WeekSection({
  professional,
  editable,
}: {
  professional: Professional;
  editable: boolean;
}) {
  const { t } = useTranslation();
  const hours = useQuery({
    queryKey: KEYS.workingHours(professional.id),
    queryFn: () => api<WorkingHours[]>(`/api/v1/professionals/${professional.id}/working-hours/`),
  });
  if (hours.isPending) return <Loading />;
  if (hours.isError) {
    return (
      <ErrorBox message={describeError(t, hours.error)} onRetry={() => void hours.refetch()} />
    );
  }
  // `key`: al cambiar de profesional el editor arranca de cero con su semana.
  return (
    <WeekEditor
      key={professional.id}
      professional={professional}
      initial={weekFromHours(hours.data)}
      editable={editable}
    />
  );
}

// --- Bloqueos -----------------------------------------------------------------------------------

function conflictsOf(error: unknown): ConflictingAppointment[] {
  if (error instanceof ApiError && error.code === "time_block_conflict") {
    const appointments = (error.fields as unknown as { appointments?: ConflictingAppointment[] })
      .appointments;
    return appointments ?? [];
  }
  return [];
}

function BlockForm({ professional, onDone }: { professional: Professional; onDone: () => void }) {
  const { t } = useTranslation();
  const formatDateTime = useTenantDateTime();
  const queryClient = useQueryClient();
  const [startAt, setStartAt] = useState("");
  const [endAt, setEndAt] = useState("");
  const [reason, setReason] = useState("");
  const invalid = Boolean(startAt && endAt && endAt <= startAt);

  // Sin zona horaria: el servidor las interpreta en la hora local del negocio.
  const create = useMutation({
    mutationFn: () =>
      api<TimeBlock>("/api/v1/time-blocks/", {
        method: "POST",
        body: { professional_id: professional.id, start_at: startAt, end_at: endAt, reason },
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: KEYS.timeBlocks(professional.id) });
      onDone();
    },
  });
  const conflicts = conflictsOf(create.error);

  return (
    <form
      noValidate
      className="grid gap-3 sm:grid-cols-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (startAt && endAt && !invalid) create.mutate();
      }}
    >
      <TextField
        label={t("catalog.hours.blockStart")}
        type="datetime-local"
        value={startAt}
        onChange={(e) => setStartAt(e.target.value)}
        required
      />
      <TextField
        label={t("catalog.hours.blockEnd")}
        type="datetime-local"
        value={endAt}
        min={startAt || undefined}
        error={invalid ? "hours_endBeforeStart" : undefined}
        onChange={(e) => setEndAt(e.target.value)}
        required
      />
      <div className="sm:col-span-2">
        <TextField
          label={t("catalog.hours.blockReason")}
          placeholder={t("catalog.hours.blockReasonPlaceholder")}
          optional
          maxLength={200}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
      </div>
      {create.isError && (
        <div className="sm:col-span-2">
          <Notice tone="danger">
            {describeError(t, create.error)}
            {conflicts.length > 0 && (
              <ul className="mt-2 list-disc pl-5">
                {conflicts.map((appointment) => (
                  <li key={appointment.id}>
                    {formatDateTime(appointment.start_at)} – {formatDateTime(appointment.end_at)}
                  </li>
                ))}
              </ul>
            )}
          </Notice>
        </div>
      )}
      <div className="flex gap-2 sm:col-span-2">
        <Button type="submit" disabled={create.isPending || !startAt || !endAt || invalid}>
          {create.isPending ? t("common.saving") : t("catalog.hours.blockSave")}
        </Button>
        <Button variant="ghost" onClick={onDone}>
          {t("common.cancel")}
        </Button>
      </div>
    </form>
  );
}

function BlocksSection({
  professional,
  editable,
}: {
  professional: Professional;
  editable: boolean;
}) {
  const { t } = useTranslation();
  const formatDateTime = useTenantDateTime();
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);
  // Solo los que aún no terminan: el pasado no se gestiona aquí.
  const [since] = useState(() => new Date().toISOString());
  const blocks = useQuery({
    queryKey: KEYS.timeBlocks(professional.id),
    queryFn: () =>
      api<Paginated<TimeBlock>>(
        `/api/v1/time-blocks/?professional_id=${professional.id}&start_at=${encodeURIComponent(since)}`,
      ),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api<void>(`/api/v1/time-blocks/${id}/`, { method: "DELETE" }),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: KEYS.timeBlocks(professional.id) }),
  });

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{t("catalog.hours.blocks")}</h2>
          <p className="text-sm text-slate-600">{t("catalog.hours.blocksHint")}</p>
        </div>
        {editable && !creating && (
          <Button variant="secondary" onClick={() => setCreating(true)}>
            {t("catalog.hours.newBlock")}
          </Button>
        )}
      </div>
      {creating && <BlockForm professional={professional} onDone={() => setCreating(false)} />}
      {blocks.isPending && <Loading />}
      {blocks.isError && (
        <ErrorBox message={describeError(t, blocks.error)} onRetry={() => void blocks.refetch()} />
      )}
      {blocks.isSuccess && blocks.data.results.length === 0 && (
        <p className="text-sm text-slate-600">{t("catalog.hours.noBlocks")}</p>
      )}
      {blocks.isSuccess && blocks.data.results.length > 0 && (
        <ul className="flex flex-col divide-y divide-slate-100">
          {blocks.data.results.map((block) => (
            <li key={block.id} className="flex flex-wrap items-center gap-3 py-3">
              <div className="min-w-0 flex-1">
                <p className="font-medium">
                  {formatDateTime(block.start_at)} – {formatDateTime(block.end_at)}
                </p>
                {block.reason && <p className="text-sm text-slate-600">{block.reason}</p>}
              </div>
              {editable && (
                <Button
                  variant="dangerGhost"
                  disabled={remove.isPending}
                  onClick={() => {
                    if (window.confirm(t("catalog.hours.deleteBlockConfirm"))) {
                      remove.mutate(block.id);
                    }
                  }}
                >
                  {t("common.delete")}
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
      {remove.isError && <Notice tone="danger">{describeError(t, remove.error)}</Notice>}
    </Card>
  );
}

// --- Página -------------------------------------------------------------------------------------

export default function HoursPage() {
  const { t } = useTranslation();
  const professionals = useProfessionals();
  const editable = useCan("schedules", "update");
  const canEditTeam = useCan("staff_services", "update");
  const [selectedId, setSelectedId] = useState("");
  const list = professionals.data ?? [];
  const selected = list.find((p) => p.id === selectedId) ?? list[0];

  return (
    <>
      <PageHeader
        title={t("dashboard.nav.hours")}
        description={editable ? t("catalog.hours.intro") : t("catalog.readOnly")}
      />
      {professionals.isPending && <Loading />}
      {professionals.isError && (
        <ErrorBox
          message={describeError(t, professionals.error)}
          onRetry={() => void professionals.refetch()}
        />
      )}
      {professionals.isSuccess && list.length === 0 && (
        <EmptyState>
          {canEditTeam ? (
            <>
              {t("catalog.hours.noTeam")}{" "}
              <Link to="/equipo" className="font-medium underline">
                {t("dashboard.nav.team")}
              </Link>
            </>
          ) : (
            // Un profesional cuya cuenta aún no está enlazada a una ficha no tiene nada propio.
            t("catalog.hours.noProfile")
          )}
        </EmptyState>
      )}
      {selected && (
        <div className="flex flex-col gap-5">
          {list.length > 1 && (
            <div className="max-w-sm">
              <SelectField
                label={t("catalog.hours.professional")}
                value={selected.id}
                onChange={(event) => setSelectedId(event.target.value)}
              >
                {list.map((professional) => (
                  <option key={professional.id} value={professional.id}>
                    {professional.display_name}
                  </option>
                ))}
              </SelectField>
            </div>
          )}
          {list.length === 1 && <h2 className="text-lg font-semibold">{selected.display_name}</h2>}
          <WeekSection professional={selected} editable={editable} />
          <BlocksSection key={selected.id} professional={selected} editable={editable} />
        </div>
      )}
    </>
  );
}
