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
  WEEKDAYS,
  copyDay,
  hasErrors,
  hoursFromWeek,
  validateWeek,
  weekFromHours,
  weeklyMinutes,
  type Week,
} from "./week";

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
  const [week, setWeek] = useState<Week>(initial);
  const [message, setMessage] = useState<{ tone: "success" | "danger"; text: string } | null>(null);
  const [showErrors, setShowErrors] = useState(false);
  const errors = validateWeek(week);

  const save = useMutation({
    mutationFn: () =>
      api<WorkingHours[]>(`/api/v1/professionals/${professional.id}/working-hours/`, {
        method: "PUT",
        body: hoursFromWeek(week),
      }),
    onSuccess: (saved) => {
      queryClient.setQueryData(KEYS.workingHours(professional.id), saved);
      setWeek(weekFromHours(saved));
      setMessage({ tone: "success", text: t("common.saved") });
    },
    onError: (error) => setMessage({ tone: "danger", text: describeError(t, error) }),
  });

  function update(weekday: number, index: number, field: "start" | "end", value: string) {
    setMessage(null);
    setWeek((current) =>
      current.map((day, d) =>
        d === weekday ? day.map((it, i) => (i === index ? { ...it, [field]: value } : it)) : day,
      ),
    );
  }
  function add(weekday: number) {
    setMessage(null);
    setWeek((current) =>
      current.map((day, d) => {
        if (d !== weekday) return day;
        const last = day.at(-1);
        // Sugerencia: la jornada típica, o una franja después de la última (tras un descanso).
        const next = last ? { start: last.end, end: "" } : { start: "09:00", end: "18:00" };
        return [...day, next];
      }),
    );
  }
  function remove(weekday: number, index: number) {
    setMessage(null);
    setWeek((current) =>
      current.map((day, d) => (d === weekday ? day.filter((_, i) => i !== index) : day)),
    );
  }

  const minutes = weeklyMinutes(week);
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
        {editable && week[0].length > 0 && (
          <Button variant="secondary" onClick={() => setWeek((w) => copyDay(w, 0, WORKDAYS))}>
            {t("catalog.hours.copyMonday")}
          </Button>
        )}
      </div>
      {message && <Notice tone={message.tone}>{message.text}</Notice>}
      <ul className="flex flex-col divide-y divide-slate-100">
        {WEEKDAYS.map((weekday) => (
          <li key={weekday} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-start">
            <span className="w-28 shrink-0 pt-2 text-sm font-medium">
              {t(`catalog.hours.days.${weekday}`)}
            </span>
            <div className="flex flex-1 flex-col gap-2">
              {week[weekday].length === 0 && (
                <p className="pt-2 text-sm text-slate-500">{t("catalog.hours.closed")}</p>
              )}
              {week[weekday].map((interval, index) => {
                const error = showErrors ? errors[weekday][index] : null;
                return (
                  <div key={index} className="flex flex-wrap items-end gap-2">
                    <div className="w-32">
                      <TextField
                        label={t("catalog.hours.from")}
                        type="time"
                        value={interval.start}
                        disabled={!editable}
                        onChange={(e) => update(weekday, index, "start", e.target.value)}
                      />
                    </div>
                    <div className="w-32">
                      <TextField
                        label={t("catalog.hours.to")}
                        type="time"
                        value={interval.end}
                        disabled={!editable}
                        error={error ? `hours_${error}` : undefined}
                        onChange={(e) => update(weekday, index, "end", e.target.value)}
                      />
                    </div>
                    {editable && (
                      <Button
                        variant="ghost"
                        aria-label={t("catalog.hours.removeInterval")}
                        onClick={() => remove(weekday, index)}
                      >
                        {t("catalog.hours.remove")}
                      </Button>
                    )}
                  </div>
                );
              })}
              {editable && (
                <div>
                  <Button variant="ghost" onClick={() => add(weekday)}>
                    {week[weekday].length === 0
                      ? t("catalog.hours.addFirst")
                      : t("catalog.hours.addBreak")}
                  </Button>
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>
      {editable && (
        <div>
          <Button
            disabled={save.isPending}
            onClick={() => {
              setShowErrors(true);
              if (!hasErrors(errors)) save.mutate();
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
                  variant="ghost"
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
