import type { CommissionEntry } from "./api";

/** Una fila del reporte de comisiones: una cita de un profesional, con todos sus servicios y sus
 *  ajustes sumados. El detalle por servicio (lo que guarda el sistema) queda en `entries`. */
export interface CommissionRow {
  key: string;
  appointmentStartAt: string;
  professionalName: string;
  services: string[];
  base: string;
  commission: string;
  business: string;
  /** El porcentaje de la cita: el mismo de sus servicios, o el efectivo si se mezclan. */
  pct: string;
  /** Suma de la comisión que movieron los ajustes ("0.00" si no hay). */
  adjustment: string;
  reasons: string[];
  entries: CommissionEntry[];
}

// Sumar en centavos enteros: con decimales de JS 0.1 + 0.2 no da 0.3.
const cents = (value: string) => Math.round(Number(value) * 100);
const money = (value: number) => (value / 100).toFixed(2);

/** Agrupa las entradas por cita y profesional, en el orden en que llegan (por fecha de la cita).
 *  Los ajustes se suman a la fila de su cita, no van aparte. */
export function commissionRows(entries: CommissionEntry[]): CommissionRow[] {
  const groups = new Map<string, CommissionEntry[]>();
  for (const entry of entries) {
    const key = `${entry.appointment_id}:${entry.professional_id}`;
    groups.set(key, [...(groups.get(key) ?? []), entry]);
  }
  return [...groups].map(([key, list]) => {
    const originals = list.filter((e) => e.kind === "entry");
    const adjustments = list.filter((e) => e.kind === "adjustment");
    const sum = (
      rows: CommissionEntry[],
      field: "base_amount" | "commission_amount" | "business_amount",
    ) => rows.reduce((total, row) => total + cents(row[field]), 0);
    const base = sum(list, "base_amount");
    const commission = sum(list, "commission_amount");
    const pcts = new Set(originals.map((e) => Number(e.pct)));
    const pct =
      adjustments.length === 0 && pcts.size === 1
        ? originals[0].pct
        : base
          ? ((commission / base) * 100).toFixed(2)
          : "0.00";
    return {
      key,
      appointmentStartAt: list[0].appointment_start_at,
      professionalName: list[0].professional_name,
      services: [...new Set((originals.length ? originals : list).map((e) => e.service_name))],
      base: money(base),
      commission: money(commission),
      business: money(sum(list, "business_amount")),
      pct,
      adjustment: money(sum(adjustments, "commission_amount")),
      reasons: adjustments.map((e) => e.reason).filter(Boolean),
      entries: list,
    };
  });
}
