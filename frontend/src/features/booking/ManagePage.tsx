import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { ApiError, api } from "../../shared/api/client";
import { describeError } from "../../shared/api/errors";
import type { AppointmentStatus, PublicAppointment } from "../../shared/api/types";
import { formatMoney } from "../../shared/money";
import {
  Badge,
  Button,
  Card,
  ErrorBox,
  Loading,
  Notice,
  TextField,
} from "../../shared/ui/primitives";
import { usePublicAppointment, usePublicCompany } from "./api";
import { formatDateTime, formatTime } from "./wizard";

const TONE: Partial<Record<AppointmentStatus, "success" | "warning" | "danger" | "info">> = {
  confirmed: "success",
  pending: "info",
  in_progress: "info",
  completed: "success",
  cancelled: "danger",
  no_show: "warning",
  rescheduled: "warning",
};

/** Resumen de una cita con su total. También se usa al confirmar una reserva. */
export function AppointmentSummary({ appointment }: { appointment: PublicAppointment }) {
  const { t, i18n } = useTranslation();
  const company = usePublicCompany().data;
  const timeZone = company?.timezone ?? "America/Bogota";
  const currency = company?.currency ?? "COP";

  return (
    <dl className="grid gap-3 sm:grid-cols-[auto_1fr] sm:gap-x-6">
      <dt className="text-sm opacity-70">{t("booking.summary.when")}</dt>
      <dd className="font-medium">
        {formatDateTime(appointment.start_at, i18n.language, timeZone)} –{" "}
        {formatTime(appointment.end_at, i18n.language, timeZone)}
      </dd>
      {appointment.attendee_name && (
        <>
          <dt className="text-sm opacity-70">{t("booking.summary.for")}</dt>
          <dd className="font-medium">{appointment.attendee_name}</dd>
        </>
      )}
      <dt className="text-sm opacity-70">{t("booking.summary.with")}</dt>
      <dd>{appointment.professional}</dd>
      <dt className="text-sm opacity-70">{t("booking.summary.where")}</dt>
      <dd>
        {appointment.location}
        {appointment.address && <span className="block opacity-80">{appointment.address}</span>}
      </dd>
      <dt className="text-sm opacity-70">{t("booking.summary.services")}</dt>
      <dd>
        <ul>
          {appointment.items.map((item, index) => (
            <li key={index}>
              {item.name} · {formatMoney(item.price, currency, i18n.language)}
            </li>
          ))}
        </ul>
      </dd>
      <dt className="text-sm opacity-70">{t("booking.summary.total")}</dt>
      <dd className="font-semibold">
        {formatMoney(appointment.price_total, currency, i18n.language)}
      </dd>
    </dl>
  );
}

export default function ManagePage() {
  const { t, i18n } = useTranslation();
  const { token = "" } = useParams();
  const queryClient = useQueryClient();
  const appointment = usePublicAppointment(token);
  const timeZone = usePublicCompany().data?.timezone ?? "America/Bogota";
  const [confirming, setConfirming] = useState(false);
  const [reason, setReason] = useState("");

  const cancel = useMutation({
    mutationFn: () =>
      api<PublicAppointment>(`/api/v1/public/appointments/${encodeURIComponent(token)}/cancel/`, {
        method: "POST",
        body: { reason },
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["public", "appointment", token], updated);
      setConfirming(false);
    },
  });

  if (appointment.isPending) return <Loading />;
  if (appointment.isError) {
    const notFound = appointment.error instanceof ApiError && appointment.error.status === 404;
    return notFound ? (
      <Notice tone="warning">{t("booking.manage.notFound")}</Notice>
    ) : (
      <ErrorBox
        message={describeError(t, appointment.error)}
        onRetry={() => void appointment.refetch()}
      />
    );
  }
  const data = appointment.data;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold">{t("booking.pages.manage.title")}</h1>
        <Badge tone={TONE[data.status] ?? "neutral"}>{t(`booking.status.${data.status}`)}</Badge>
      </div>
      <p>{t("booking.manage.hello", { name: data.customer_name })}</p>
      <Card className="!bg-[var(--color-surface,#ffffff)]">
        <AppointmentSummary appointment={data} />
      </Card>
      {cancel.isSuccess && <Notice tone="success">{t("booking.manage.cancelled")}</Notice>}
      {data.can_cancel && !confirming && (
        <div className="flex flex-col gap-2">
          <p className="text-sm opacity-80">
            {t("booking.manage.cancelUntil", {
              deadline: formatDateTime(data.cancel_deadline, i18n.language, timeZone),
            })}
          </p>
          <div>
            <Button variant="secondary" onClick={() => setConfirming(true)}>
              {t("booking.manage.cancel")}
            </Button>
          </div>
        </div>
      )}
      {data.can_cancel && confirming && (
        <Card className="flex flex-col gap-3">
          <p className="font-medium">{t("booking.manage.confirmCancel")}</p>
          <TextField
            label={t("booking.manage.reason")}
            optional
            maxLength={250}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
          {cancel.isError && <Notice tone="danger">{describeError(t, cancel.error)}</Notice>}
          <div className="flex flex-wrap gap-2">
            <Button variant="danger" disabled={cancel.isPending} onClick={() => cancel.mutate()}>
              {cancel.isPending ? t("common.saving") : t("booking.manage.confirmCancelButton")}
            </Button>
            <Button variant="ghost" onClick={() => setConfirming(false)}>
              {t("booking.manage.keep")}
            </Button>
          </div>
        </Card>
      )}
      {!data.can_cancel && data.status === "confirmed" && (
        <Notice tone="info">{t("booking.manage.tooLate")}</Notice>
      )}
      <Link to="/reservar" className="underline">
        {t("booking.manage.bookAnother")}
      </Link>
    </div>
  );
}
