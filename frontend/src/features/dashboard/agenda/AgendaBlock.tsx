import { useTranslation } from "react-i18next";
import type { Appointment, AppointmentStatus } from "../../../shared/api/types";
import { formatTime } from "../../booking/wizard";
import { useServices } from "../shared/api";

/** Fondo suave y borde izquierdo por estado: la agenda se lee de un vistazo sin abrir la cita. */
const STATUS_STYLE: Record<AppointmentStatus, string> = {
  pending: "bg-amber-50 border-amber-200 before:bg-amber-500",
  confirmed: "bg-[#fbeeec] border-[#efc7c1] before:bg-[#b8352b]",
  in_progress: "bg-sky-50 border-sky-200 before:bg-sky-600",
  completed: "bg-emerald-50 border-emerald-200 before:bg-emerald-600",
  cancelled: "bg-slate-100 border-slate-200 before:bg-slate-400",
  no_show: "bg-slate-100 border-slate-200 before:bg-slate-400",
  rescheduled: "bg-slate-100 border-slate-200 before:bg-slate-400",
};

const INACTIVE: AppointmentStatus[] = ["cancelled", "no_show", "rescheduled"];

/** Bloque de una cita en la grilla de la agenda. Sin barras de desplazamiento: muestra lo que
 *  cabe según su alto (hora, cliente, servicios, estado) y el resto va en el título emergente y
 *  en el nombre accesible. Al tocarlo se abre el detalle completo. */
export function AgendaBlock({
  appointment,
  height,
  timeZone,
  professional,
  onOpen,
  style,
}: {
  appointment: Appointment;
  height: number;
  timeZone: string;
  professional?: string;
  onOpen: () => void;
  style: React.CSSProperties;
}) {
  const { t, i18n } = useTranslation();
  const services = useServices();
  const time = (iso: string) => formatTime(iso, i18n.language, timeZone);
  const range = `${time(appointment.start_at)} – ${time(appointment.end_at)}`;
  const who = appointment.attendee_name
    ? `${appointment.customer.full_name} · ${t("agenda.attendee", { name: appointment.attendee_name })}`
    : appointment.customer.full_name;
  const serviceNames = appointment.items
    .map(
      (item) =>
        services.data?.find((s) => s.id === item.service_id)?.name ?? t("agenda.unknownService"),
    )
    .join(", ");
  const status = t(`agenda.status.${appointment.status}`);
  const full = [range, who, serviceNames, professional, status].filter(Boolean).join(" · ");
  const inactive = INACTIVE.includes(appointment.status);
  // Por alto disponible: una línea, dos o la tarjeta completa.
  const size = height < 44 ? "line" : height < 76 ? "short" : "full";

  return (
    <button
      type="button"
      title={full}
      aria-label={full}
      onClick={onOpen}
      style={style}
      className={`absolute flex overflow-hidden rounded-lg border pl-1.5 text-left text-xs text-[var(--pf-ink,#171111)] transition-[filter] before:absolute before:inset-y-0 before:left-0 before:w-1 hover:z-20 hover:brightness-[0.97] focus-visible:z-30 focus-visible:outline-2 ${
        STATUS_STYLE[appointment.status]
      } ${inactive ? "opacity-70" : ""}`}
    >
      <span className="flex min-w-0 flex-1 flex-col gap-0.5 px-2 py-1 leading-4">
        {size === "line" ? (
          <span className="truncate">
            <span className="font-semibold tabular-nums">{time(appointment.start_at)}</span>{" "}
            <span className={inactive ? "line-through" : ""}>{appointment.customer.full_name}</span>
          </span>
        ) : (
          <>
            <span className="flex items-center justify-between gap-2">
              <span className="truncate font-semibold tabular-nums">{range}</span>
              {size === "full" && (
                <span className="shrink-0 text-[11px] text-[var(--pf-muted,#5c4f4d)]">
                  {status}
                </span>
              )}
            </span>
            <span
              className={`truncate text-[13px] leading-4 font-semibold ${inactive ? "line-through" : ""}`}
            >
              {who}
            </span>
            {size === "full" && (
              <span className="line-clamp-2 text-[var(--pf-muted,#5c4f4d)]">{serviceNames}</span>
            )}
          </>
        )}
      </span>
    </button>
  );
}
