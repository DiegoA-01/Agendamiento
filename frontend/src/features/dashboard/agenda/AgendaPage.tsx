import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import {
  Badge,
  Button,
  Card,
  CheckboxField,
  EmptyState,
  ErrorBox,
  Loading,
  PageHeader,
  SelectField,
} from "../../../shared/ui/primitives";
import { describeError } from "../../../shared/api/errors";
import { useMe } from "../../auth/useMe";
import { formatDay, todayIn } from "../../booking/wizard";
import { useProfessionals, useServices } from "../shared/api";
import { useCan } from "../shared/useCan";
import { useAgendaAppointments } from "../appointments/api";
import { AppointmentForm } from "../appointments/AppointmentForm";
import { AppointmentDetail, AppointmentSummary } from "../appointments/AppointmentDetail";
import { AgendaBlock } from "./AgendaBlock";
import { addDays, layoutBlocks, dateFilters, groupAppointments, weekDays } from "./calendar";
import { useAppointmentEvents } from "./useAppointmentEvents";

const FIRST_VISIBLE_HOUR = 7;
// Píxeles por minuto de la grilla: 96 px por hora, así una cita de 30 min se lee completa.
const SCALE = 1.6;
const HOUR_PX = 60 * SCALE;
const HIDDEN_STATUSES = ["cancelled", "no_show", "rescheduled"];

export default function AgendaPage() {
  const { t, i18n } = useTranslation();
  const zone = useMe().data?.tenant?.timezone ?? "America/Bogota";
  const [date, setDate] = useState(() => todayIn(zone));
  const [view, setView] = useState<"day" | "week">("day");
  const scrolled = useRef(false);
  const [professional, setProfessional] = useState("");
  // Las canceladas, inasistencias y reprogramadas ocupan carriles y angostan las demás: se
  // ocultan por defecto y se pueden mostrar.
  const [showInactive, setShowInactive] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  // "Nueva cita" del Inicio llega con `?nueva=1` y abre el formulario de una vez.
  const [params] = useSearchParams();
  const [creating, setCreating] = useState(() => params.get("nueva") === "1");
  const live = useAppointmentEvents();
  const canCreate = useCan("appointments", "create");
  const professionals = useProfessionals();
  const services = useServices();
  const dates = view === "day" ? [date] : weekDays(date);
  const appointments = useAgendaAppointments({
    ...dateFilters(dates[0], dates[dates.length - 1]),
    professional_id: professional,
  });
  const list = (appointments.data ?? []).filter(
    (a) => showInactive || !HIDDEN_STATUSES.includes(a.status),
  );
  const ids = Array.from(
    new Set([
      ...(professionals.data ?? []).map((p) => p.id),
      ...list.map((a) => a.professional_id),
    ]),
  ).filter((id) => !professional || id === professional);
  const groups = groupAppointments(list, dates, ids, zone);
  const columns =
    view === "day"
      ? groups[0].professionals.map((p) => ({
          key: p.id,
          date,
          title:
            professionals.data?.find((item) => item.id === p.id)?.display_name ??
            t("agenda.professional"),
          appointments: p.appointments,
        }))
      : groups.map((day) => ({
          key: day.date,
          date: day.date,
          title: formatDay(day.date, i18n.language),
          appointments: day.professionals.flatMap((p) => p.appointments),
        }));
  const failed = appointments.isError
    ? appointments
    : professionals.isError
      ? professionals
      : services.isError
        ? services
        : null;
  const ready = appointments.isSuccess && professionals.isSuccess && services.isSuccess;
  return (
    <div className="min-w-0 space-y-5">
      <PageHeader
        title={t("dashboard.nav.agenda")}
        description={t("agenda.agendaIntro")}
        actions={
          <>
            {canCreate && (
              <Button onClick={() => setCreating(true)}>{t("agenda.newAppointment")}</Button>
            )}
            <span role="status">
              <Badge tone={live ? "success" : "warning"}>
                {t(live ? "agenda.live" : "agenda.reconnecting")}
              </Badge>
            </span>
          </>
        }
      />
      <Card className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {(["day", "week"] as const).map((value) => (
            <Button
              key={value}
              variant={view === value ? "primary" : "secondary"}
              aria-pressed={view === value}
              onClick={() => setView(value)}
            >
              {t(`agenda.${value}`)}
            </Button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            onClick={() => setDate(addDays(date, view === "day" ? -1 : -7))}
          >
            {t("agenda.previous")}
          </Button>
          <Button variant="secondary" onClick={() => setDate(todayIn(zone))}>
            {t("agenda.today")}
          </Button>
          <Button
            variant="secondary"
            onClick={() => setDate(addDays(date, view === "day" ? 1 : 7))}
          >
            {t("agenda.next")}
          </Button>
        </div>
        <p className="font-medium">
          {formatDay(dates[0], i18n.language)}
          {view === "week" && ` – ${formatDay(dates[6], i18n.language)}`}
        </p>
        <SelectField
          label={t("agenda.professional")}
          value={professional}
          onChange={(e) => setProfessional(e.target.value)}
        >
          <option value="">{t("common.all")}</option>
          {professionals.data?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.display_name}
            </option>
          ))}
        </SelectField>
        <CheckboxField
          label={t("agenda.showInactive")}
          checked={showInactive}
          onChange={(e) => setShowInactive(e.target.checked)}
        />
      </Card>
      {creating && (
        <Card>
          <AppointmentForm onDone={() => setCreating(false)} />
        </Card>
      )}
      {selected && <AppointmentDetail id={selected} onClose={() => setSelected(null)} />}
      {(appointments.isPending || professionals.isPending || services.isPending) && <Loading />}
      {failed && (
        <ErrorBox message={describeError(t, failed.error)} onRetry={() => void failed.refetch()} />
      )}
      {ready && !list.length && <EmptyState>{t("agenda.emptyAppointments")}</EmptyState>}
      {ready && view === "day" && (
        <div className="space-y-3 sm:hidden">
          {list.map((a) => (
            <button
              key={a.id}
              className="w-full rounded-xl border border-slate-200 bg-white p-4 focus-visible:outline-2 focus-visible:outline-sky-700"
              onClick={() => setSelected(a.id)}
            >
              <AppointmentSummary appointment={a} />
              <p className="mt-2 text-left text-sm">
                {professionals.data?.find((p) => p.id === a.professional_id)?.display_name}
              </p>
            </button>
          ))}
        </div>
      )}
      {ready && columns.length > 0 && (
        <div
          className={`max-h-[70vh] max-w-full min-w-0 overflow-auto rounded-xl border border-slate-200 bg-white ${view === "day" ? "hidden sm:block" : ""}`}
          // La grilla mide 24 h (1 px por minuto): abre a primera hora del día laboral.
          ref={(element) => {
            if (element && !scrolled.current) {
              element.scrollTop = FIRST_VISIBLE_HOUR * HOUR_PX;
              scrolled.current = true;
            }
          }}
          tabIndex={0}
          role="region"
          aria-label={t("agenda.grid")}
        >
          <div
            className="grid"
            style={{
              gridTemplateColumns: `56px repeat(${columns.length}, minmax(190px, 1fr))`,
              minWidth: 56 + columns.length * 190,
            }}
          >
            <div aria-hidden="true" className="sticky top-0 z-10 bg-white" />
            {columns.map((column) => (
              <h2
                key={column.key}
                className="sticky top-0 z-10 border-b border-l border-slate-200 bg-white p-3 text-sm font-semibold"
              >
                {column.title}
              </h2>
            ))}
            <div className="relative text-xs text-slate-600" style={{ height: 24 * HOUR_PX }}>
              {Array.from({ length: 24 }, (_, hour) => (
                <span
                  key={hour}
                  className="absolute right-2 -translate-y-1/2 tabular-nums"
                  style={{ top: hour * HOUR_PX }}
                >
                  {String(hour).padStart(2, "0")}:00
                </span>
              ))}
            </div>
            {columns.map((column) => (
              <div
                key={column.key}
                className="relative border-l border-slate-200"
                style={{
                  height: 24 * HOUR_PX,
                  // Línea de cada hora y una más tenue en la media hora, para ubicar bien cada cita.
                  backgroundImage: `repeating-linear-gradient(to bottom, #e4ddef 0, #e4ddef 1px, transparent 1px, transparent ${HOUR_PX / 2}px, #efeaf6 ${HOUR_PX / 2}px, #efeaf6 ${HOUR_PX / 2 + 1}px, transparent ${HOUR_PX / 2 + 1}px, transparent ${HOUR_PX}px)`, // taste-skill-ignore: son las líneas de la grilla, no un degradado
                }}
              >
                {layoutBlocks(column.appointments, column.date, zone).map(
                  ({ appointment, top, height, left, width }) => (
                    <AgendaBlock
                      key={appointment.id}
                      appointment={appointment}
                      height={height * SCALE - 4}
                      timeZone={zone}
                      professional={
                        view === "week"
                          ? professionals.data?.find((p) => p.id === appointment.professional_id)
                              ?.display_name
                          : undefined
                      }
                      onOpen={() => setSelected(appointment.id)}
                      // 2 px de aire entre bloques vecinos, para que no se peguen.
                      style={{
                        top: top * SCALE + 2,
                        height: height * SCALE - 4,
                        left: `calc(${left}% + 2px)`,
                        width: `calc(${width}% - 4px)`,
                      }}
                    />
                  ),
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
