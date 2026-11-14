import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import {
  Badge,
  Button,
  Card,
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
import { addDays, layoutBlocks, dateFilters, groupAppointments, weekDays } from "./calendar";
import { useAppointmentEvents } from "./useAppointmentEvents";

const FIRST_VISIBLE_HOUR = 7;

export default function AgendaPage() {
  const { t, i18n } = useTranslation();
  const zone = useMe().data?.tenant?.timezone ?? "America/Bogota";
  const [date, setDate] = useState(() => todayIn(zone));
  const [view, setView] = useState<"day" | "week">("day");
  const scrolled = useRef(false);
  const [professional, setProfessional] = useState("");
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
  const list = appointments.data ?? [];
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
              element.scrollTop = FIRST_VISIBLE_HOUR * 60;
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
            <div className="relative h-[1440px] text-xs text-slate-600">
              {Array.from({ length: 24 }, (_, hour) => (
                <span key={hour} className="absolute right-2" style={{ top: hour * 60 }}>
                  {String(hour).padStart(2, "0")}:00
                </span>
              ))}
            </div>
            {columns.map((column) => (
              <div
                key={column.key}
                className="relative h-[1440px] border-l border-slate-200"
                style={{
                  backgroundImage:
                    "repeating-linear-gradient(to bottom, transparent 0, transparent 59px, #e2e8f0 59px, #e2e8f0 60px)",
                }}
              >
                {layoutBlocks(column.appointments, column.date, zone).map(
                  ({ appointment, top, height, left, width }) => (
                    <button
                      key={appointment.id}
                      className="absolute overflow-auto rounded-md border border-sky-300 bg-sky-50 p-1 text-xs text-slate-900 hover:bg-sky-100 focus-visible:z-50 focus-visible:outline-2 focus-visible:outline-sky-700"
                      style={{ top, height, left: `${left}%`, width: `${width}%` }}
                      onClick={() => setSelected(appointment.id)}
                    >
                      <AppointmentSummary appointment={appointment} />
                    </button>
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
