import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../../shared/api/client";
import { describeError } from "../../../shared/api/errors";
import type { Appointment } from "../../../shared/api/types";
import {
  Badge,
  Button,
  Card,
  ErrorBox,
  Loading,
  Notice,
  SelectField,
  TextField,
} from "../../../shared/ui/primitives";
import { formatMoney } from "../../../shared/money";
import { useMe } from "../../auth/useMe";
import { formatDateTime, todayIn } from "../../booking/wizard";
import { KEYS, useProfessionals, useServices } from "../shared/api";
import { useCan } from "../shared/useCan";
import { useRefreshAppointments } from "./api";
import { allowedActions, type AppointmentAction } from "./transitions";
import { SlotPicker } from "./SlotPicker";

export function AppointmentSummary({ appointment }: { appointment: Appointment }) {
  const { t, i18n } = useTranslation();
  const me = useMe().data;
  const services = useServices();
  return (
    <div className="min-w-0 space-y-1 break-words text-left">
      <p className="text-xs">
        {formatDateTime(
          appointment.start_at,
          i18n.language,
          me?.tenant?.timezone ?? "America/Bogota",
        )}
      </p>
      <p className="font-semibold">{appointment.customer.full_name}</p>
      <p className="text-xs">
        {appointment.items
          .map(
            (item) =>
              services.data?.find((s) => s.id === item.service_id)?.name ??
              t("agenda.unknownService"),
          )
          .join(", ")}
      </p>
      <Badge
        tone={
          appointment.status === "completed"
            ? "success"
            : appointment.status === "confirmed"
              ? "info"
              : appointment.status === "cancelled" || appointment.status === "no_show"
                ? "danger"
                : appointment.status === "pending"
                  ? "warning"
                  : "neutral"
        }
      >
        {t(`agenda.status.${appointment.status}`)}
      </Badge>
    </div>
  );
}

function ActionButton({
  action,
  onClick,
  disabled,
}: {
  action: AppointmentAction;
  onClick: () => void;
  disabled: boolean;
}) {
  const { t } = useTranslation();
  const permitted = useCan("appointments", action);
  if (!permitted) return null;
  return (
    <Button
      variant={action === "cancel" ? "danger" : "secondary"}
      disabled={disabled}
      onClick={onClick}
    >
      {t(`agenda.actions.${action}`)}
    </Button>
  );
}

function DetailContent({
  appointment,
  onClose,
}: {
  appointment: Appointment;
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation();
  const me = useMe().data;
  const zone = me?.tenant?.timezone ?? "America/Bogota";
  const professionals = useProfessionals();
  const refresh = useRefreshAppointments();
  const [editing, setEditing] = useState<"cancel" | "reschedule" | null>(null);
  const [reason, setReason] = useState("");
  const [date, setDate] = useState(todayIn(zone, new Date(appointment.start_at)));
  const [professional, setProfessional] = useState(appointment.professional_id);
  const [start, setStart] = useState("");
  const cancelAllowed =
    useCan("appointments", "cancel") && allowedActions(appointment.status).includes("cancel");
  const rescheduleAllowed =
    useCan("appointments", "reschedule") &&
    allowedActions(appointment.status).includes("reschedule");
  const mutation = useMutation({
    mutationFn: (action: AppointmentAction) =>
      api<Appointment>(
        `/api/v1/appointments/${appointment.id}/${action === "no_show" ? "no-show" : action}/`,
        {
          method: "POST",
          body:
            action === "cancel"
              ? { reason }
              : action === "reschedule"
                ? { start_at: start, professional_id: professional || null }
                : undefined,
        },
      ),
    onSuccess: () => {
      refresh();
      onClose();
    },
    onError: (error) => {
      if (error instanceof ApiError && ["invalid_transition", "slot_taken"].includes(error.code)) {
        refresh();
        setStart("");
      }
    },
  });
  const suggestions =
    mutation.error instanceof ApiError && mutation.error.code === "slot_taken"
      ? (mutation.error.fields.suggestions ?? [])
      : [];
  return (
    <Card className="space-y-4 border-sky-300" aria-label={t("agenda.detail")}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h2 className="text-lg font-semibold">{t("agenda.detail")}</h2>
        <Button variant="ghost" onClick={onClose}>
          {t("agenda.close")}
        </Button>
      </div>
      <AppointmentSummary appointment={appointment} />
      <p>{formatDateTime(appointment.end_at, i18n.language, zone)}</p>
      <p>{professionals.data?.find((p) => p.id === appointment.professional_id)?.display_name}</p>
      <p className="break-words">
        {appointment.customer.phone} · {appointment.customer.email}
      </p>
      <p>{formatMoney(appointment.price_total, me?.tenant?.currency ?? "COP", i18n.language)}</p>
      {appointment.cancel_reason && <p>{appointment.cancel_reason}</p>}
      <div className="flex flex-wrap gap-2">
        {allowedActions(appointment.status).map((action) => (
          <ActionButton
            key={action}
            action={action}
            disabled={mutation.isPending}
            onClick={() => {
              mutation.reset();
              if (action === "cancel" || action === "reschedule") setEditing(action);
              else mutation.mutate(action);
            }}
          />
        ))}
      </div>
      {editing === "cancel" && cancelAllowed && (
        <div className="space-y-3">
          <TextField
            label={t("agenda.reason")}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <Button
            variant="danger"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate("cancel")}
          >
            {t("agenda.actions.cancel")}
          </Button>
        </div>
      )}
      {editing === "reschedule" && rescheduleAllowed && (
        <div className="space-y-3">
          <SelectField
            label={t("agenda.professional")}
            value={professional}
            onChange={(e) => {
              setProfessional(e.target.value);
              setStart("");
              mutation.reset();
            }}
          >
            <option value="">{t("agenda.anyone")}</option>
            {professionals.data?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.display_name}
              </option>
            ))}
          </SelectField>
          <TextField
            label={t("agenda.date")}
            type="date"
            value={date}
            onChange={(e) => {
              setDate(e.target.value);
              setStart("");
              mutation.reset();
            }}
          />
          <SlotPicker
            serviceIds={appointment.items.map((item) => item.service_id)}
            professionalId={professional}
            date={date}
            value={start}
            onChange={setStart}
          />
          <Button
            disabled={!start || mutation.isPending}
            onClick={() => mutation.mutate("reschedule")}
          >
            {t("agenda.actions.reschedule")}
          </Button>
        </div>
      )}
      {mutation.isError && <Notice tone="danger">{describeError(t, mutation.error)}</Notice>}
      {editing === "reschedule" && suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {suggestions.map((value) => (
            <Button
              key={value}
              aria-pressed={start === value}
              variant="secondary"
              onClick={() => {
                setDate(todayIn(zone, new Date(value)));
                setStart(value);
              }}
            >
              {formatDateTime(value, i18n.language, zone)}
            </Button>
          ))}
        </div>
      )}
    </Card>
  );
}

export function AppointmentDetail({ id, onClose }: { id: string; onClose: () => void }) {
  const { t } = useTranslation();
  const detail = useQuery({
    queryKey: [...KEYS.appointments, "detail", id],
    queryFn: () => api<Appointment>(`/api/v1/appointments/${id}/`),
  });
  if (detail.isPending) return <Loading />;
  if (detail.isError)
    return (
      <ErrorBox message={describeError(t, detail.error)} onRetry={() => void detail.refetch()} />
    );
  return <DetailContent key={id} appointment={detail.data} onClose={onClose} />;
}
