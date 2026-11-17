import { useRef, type PointerEvent } from "react";
import { useTranslation } from "react-i18next";
import type { PublicAppointment } from "../../shared/api/types";
import { formatMoney } from "../../shared/money";
import { usePublicCompany } from "./api";
import { formatDateTime, formatTime } from "./wizard";

/** La cita como una tarjeta de billetera (wallet): verde metalizado brillante, con chip, un brillo
 *  que sigue al cursor y una leve inclinación 3D. Muestra lo mismo que el resumen de la cita; los
 *  rótulos van en texto para lectores de pantalla. */
export function WalletCard({
  appointment,
  status,
  dimmed = false,
}: {
  appointment: PublicAppointment;
  status?: string;
  dimmed?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const company = usePublicCompany().data;
  const timeZone = company?.timezone ?? "America/Bogota";
  const currency = company?.currency ?? "COP";
  const ref = useRef<HTMLElement>(null);

  // Inclinación y brillo según dónde esté el cursor (solo con mouse; en el celular queda quieta).
  function tilt(event: PointerEvent<HTMLElement>) {
    const el = ref.current;
    if (!el || event.pointerType !== "mouse") return;
    const box = el.getBoundingClientRect();
    const x = (event.clientX - box.left) / box.width;
    const y = (event.clientY - box.top) / box.height;
    el.style.setProperty("--mx", `${Math.round(x * 100)}%`);
    el.style.setProperty("--my", `${Math.round(y * 100)}%`);
    el.style.setProperty("--ry", `${((x - 0.5) * 10).toFixed(2)}deg`);
    el.style.setProperty("--rx", `${((0.5 - y) * 8).toFixed(2)}deg`);
  }
  function reset() {
    const el = ref.current;
    if (!el) return;
    for (const name of ["--mx", "--my", "--ry", "--rx"]) el.style.removeProperty(name);
  }

  const date = formatDateTime(appointment.start_at, i18n.language, timeZone);
  const end = formatTime(appointment.end_at, i18n.language, timeZone);

  return (
    <article
      ref={ref}
      onPointerMove={tilt}
      onPointerLeave={reset}
      aria-label={t("booking.wallet.label")}
      className={`wallet-card ${dimmed ? "wallet-card-dimmed" : ""}`}
    >
      <div className="relative z-10 flex h-full flex-col gap-5">
        <div className="flex items-start justify-between gap-3">
          <p className="text-sm font-semibold tracking-[0.14em] uppercase">{company?.name ?? ""}</p>
          {status && <span className="wallet-pill">{status}</span>}
        </div>

        <div className="flex items-center gap-3" aria-hidden="true">
          <span className="wallet-chip" />
          <svg
            viewBox="0 0 24 24"
            className="size-6 opacity-80"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          >
            <path d="M8.5 7.5a7 7 0 0 1 0 9M12 5a10.5 10.5 0 0 1 0 14M15.5 2.8a14 14 0 0 1 0 18.4" />
          </svg>
        </div>

        <div>
          <p className="sr-only">{t("booking.summary.when")}</p>
          <p className="wallet-emboss text-xl font-semibold first-letter:uppercase sm:text-2xl">
            {date} – {end}
          </p>
        </div>

        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          {appointment.attendee_name && (
            <div>
              <dt className="wallet-label">{t("booking.summary.for")}</dt>
              <dd className="font-medium">{appointment.attendee_name}</dd>
            </div>
          )}
          <div>
            <dt className="wallet-label">{t("booking.summary.with")}</dt>
            <dd className="font-medium">{appointment.professional}</dd>
          </div>
          <div>
            <dt className="wallet-label">{t("booking.summary.where")}</dt>
            <dd className="font-medium">
              {appointment.location}
              {appointment.address && (
                <span className="block font-normal opacity-80">{appointment.address}</span>
              )}
            </dd>
          </div>
          <div className="col-span-2">
            <dt className="wallet-label">{t("booking.summary.services")}</dt>
            <dd>
              <ul>
                {appointment.items.map((item, index) => (
                  <li key={index}>
                    {item.name} · {formatMoney(item.price, currency, i18n.language)}
                  </li>
                ))}
              </ul>
            </dd>
          </div>
        </dl>

        <div className="mt-auto flex items-end justify-between gap-4 pt-2">
          <p className="min-w-0 truncate text-sm tracking-[0.12em] uppercase opacity-90">
            {appointment.customer_name}
          </p>
          <div className="text-right">
            <p className="wallet-label">{t("booking.summary.total")}</p>
            <p className="wallet-emboss text-2xl font-bold tabular-nums">
              {formatMoney(appointment.price_total, currency, i18n.language)}
            </p>
          </div>
        </div>
      </div>
    </article>
  );
}
