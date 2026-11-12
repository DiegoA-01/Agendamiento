import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../shared/api/client";
import { describeError } from "../../shared/api/errors";
import type { PublicAppointment } from "../../shared/api/types";
import { Notice, TextField } from "../../shared/ui/primitives";
import { usePublicCompany } from "./api";
import { formatDateTime } from "./wizard";

const BUTTON =
  "min-h-12 rounded-2xl px-5 font-medium focus-visible:outline-2 transition-transform active:scale-[0.98]";

/** Cancelar la cita por su enlace, en la confirmación de la reserva y en la página de la cita.
 *  El servidor decide si aún se puede (hasta `cancel_min_hours` antes, 1 h por defecto). */
export function CancelAppointment({
  token,
  canCancel,
  deadline,
  onCancelled,
}: {
  token: string;
  canCancel: boolean;
  deadline: string;
  onCancelled: (appointment: PublicAppointment) => void;
}) {
  const { t, i18n } = useTranslation();
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
      setConfirming(false);
      onCancelled(updated);
    },
  });

  if (!canCancel) {
    return <Notice tone="info">{t("booking.manage.tooLate")}</Notice>;
  }

  if (!confirming) {
    return (
      <div className="flex flex-col gap-2">
        <button
          type="button"
          onClick={() => setConfirming(true)}
          className={`${BUTTON} bg-[var(--color-surface)] text-[var(--color-text)] ring-1 ring-[color-mix(in_srgb,var(--color-text)_25%,transparent)] ring-inset`}
        >
          {t("booking.manage.cancel")}
        </button>
        <p className="text-sm opacity-80">
          {t("booking.manage.cancelUntil", {
            deadline: formatDateTime(deadline, i18n.language, timeZone),
          })}
        </p>
      </div>
    );
  }

  return (
    <section
      aria-labelledby="cancel-title"
      className="flex flex-col gap-3 rounded-2xl bg-[var(--color-surface)] p-4"
    >
      <h2 id="cancel-title" className="font-medium">
        {t("booking.manage.confirmCancel")}
      </h2>
      <TextField
        label={t("booking.manage.reason")}
        optional
        maxLength={250}
        value={reason}
        onChange={(event) => setReason(event.target.value)}
      />
      {cancel.isError && <Notice tone="danger">{describeError(t, cancel.error)}</Notice>}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={cancel.isPending}
          onClick={() => cancel.mutate()}
          className={`${BUTTON} bg-red-700 text-white hover:bg-red-800 disabled:opacity-60`}
        >
          {cancel.isPending ? t("common.saving") : t("booking.manage.confirmCancelButton")}
        </button>
        <button
          type="button"
          onClick={() => setConfirming(false)}
          className={`${BUTTON} text-[var(--color-text)] underline underline-offset-4`}
        >
          {t("booking.manage.keep")}
        </button>
      </div>
    </section>
  );
}
