import type {
  AvailableDays,
  DayStatus,
  PublicCategory,
  PublicService,
  Slot,
  SlotPeriod,
} from "../../shared/api/types";

/** Pasos del asistente de reserva (spec §13): servicios → profesional → fecha → hora → datos. */
// R9: tres pasos. Profesional, día y hora van juntos en `schedule`.
export const STEPS = ["services", "schedule", "details"] as const;
export type Step = (typeof STEPS)[number];

export const MAX_SERVICES = 10;
export const PERIODS: SlotPeriod[] = ["morning", "afternoon", "evening"];

export interface Customer {
  full_name: string;
  phone: string;
  email: string;
}

/** Servicios elegidos, en el orden en que aparecen en el catálogo (el último aporta el tiempo de
 *  preparación en el servidor; así el orden no depende de los clics). */
export function selectedServices(categories: PublicCategory[], ids: string[]): PublicService[] {
  return categories.flatMap((category) => category.services).filter((s) => ids.includes(s.id));
}

export function totals(services: PublicService[]): { minutes: number; price: string } {
  const minutes = services.reduce((sum, service) => sum + service.duration_min, 0);
  // Centavos enteros: sumar decimales como float da 0.30000000000000004.
  const cents = services.reduce((sum, service) => sum + Math.round(Number(service.price) * 100), 0);
  return { minutes, price: (cents / 100).toFixed(2) };
}

/** Fecha de hoy (YYYY-MM-DD) en la zona del negocio, no en la del navegador. */
export function todayIn(timeZone: string, now: Date = new Date()): string {
  // en-CA formatea como YYYY-MM-DD.
  return new Intl.DateTimeFormat("en-CA", { timeZone }).format(now);
}

export function monthOf(date: string): string {
  return date.slice(0, 7);
}

export function addMonths(month: string, delta: number): string {
  const [year, m] = month.split("-").map(Number);
  const total = year * 12 + (m - 1) + delta;
  return `${Math.floor(total / 12)}-${String((total % 12) + 1).padStart(2, "0")}`;
}

/** Celdas del calendario del mes, semanas de lunes a domingo; `null` = hueco antes del día 1. */
export function calendarCells(month: string): (string | null)[] {
  const [year, m] = month.split("-").map(Number);
  const first = new Date(Date.UTC(year, m - 1, 1));
  const days = new Date(Date.UTC(year, m, 0)).getUTCDate();
  const leading = (first.getUTCDay() + 6) % 7; // lunes = 0
  return [
    ...Array<null>(leading).fill(null),
    ...Array.from({ length: days }, (_, i) => `${month}-${String(i + 1).padStart(2, "0")}`),
  ];
}

export function slotsByPeriod(slots: Slot[]): Record<SlotPeriod, Slot[]> {
  const groups: Record<SlotPeriod, Slot[]> = { morning: [], afternoon: [], evening: [] };
  for (const slot of slots) groups[slot.period]?.push(slot);
  return groups;
}

/** Cuerpo de `POST /public/appointments/`. `website` es el honeypot: una persona no lo ve. */
export function bookingPayload(input: {
  serviceIds: string[];
  professionalId: string | null;
  start: string;
  customer: Customer;
  acceptDataPolicy: boolean;
  marketingConsent: boolean;
  website: string;
}) {
  return {
    service_ids: input.serviceIds,
    professional_id: input.professionalId,
    start_at: input.start,
    customer: {
      full_name: input.customer.full_name.trim(),
      phone: input.customer.phone.trim(),
      email: input.customer.email.trim(),
    },
    accept_data_policy: input.acceptDataPolicy,
    marketing_consent: input.marketingConsent,
    website: input.website,
  };
}

/** Celular colombiano o internacional: 7 a 15 dígitos, con +, espacios, guiones o paréntesis.
 *  El servidor lo normaliza a E.164; esto solo evita enviar algo que claramente no es un número. */
export function looksLikePhone(value: string): boolean {
  if (!/^[+\d\s()-]+$/.test(value.trim())) return false;
  const digits = value.replace(/\D/g, "");
  return digits.length >= 7 && digits.length <= 15;
}

export function formatTime(iso: string, locale: string, timeZone: string): string {
  return new Intl.DateTimeFormat(locale, { timeStyle: "short", timeZone }).format(new Date(iso));
}

export function formatDay(date: string, locale: string): string {
  // Mediodía UTC: el día no cambia al formatear en ninguna zona horaria.
  return new Intl.DateTimeFormat(locale, {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  }).format(new Date(`${date}T12:00:00Z`));
}

export function formatDateTime(iso: string, locale: string, timeZone: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "full",
    timeStyle: "short",
    timeZone,
  }).format(new Date(iso));
}

/** Estado de cada fecha del mes. Si la API aún no manda `calendar`, usa `days` (los demás quedan
 *  como no disponibles). Una fecha que no viene se trata como no disponible. */
export function dayStatuses(data: AvailableDays | undefined): Map<string, DayStatus> {
  const statuses = new Map<string, DayStatus>();
  if (!data) return statuses;
  if (data.calendar) {
    for (const { date, status } of data.calendar) statuses.set(date, status);
  } else {
    for (const date of data.days) statuses.set(date, "available");
  }
  return statuses;
}

/** Clases de cada estado en el calendario. El color nunca va solo: el estado también va en el
 *  nombre accesible del botón y en la leyenda. */
export const DAY_STYLES: Record<DayStatus, string> = {
  // Colores del tema del negocio (R9): sirven igual con un tema claro o uno oscuro.
  available: "bg-[var(--color-surface)] text-[var(--color-text)] hover:bg-[var(--bk-raised)]",
  full: "text-[var(--bk-muted)] line-through ring-1 ring-inset ring-[var(--bk-line)]",
  closed: "text-[var(--bk-muted)] opacity-60",
  unavailable: "text-[var(--bk-muted)] opacity-30",
};

/** Agrega o quita un servicio de la selección (R3). En una categoría "solo uno por cita", elegir
 *  otro servicio reemplaza al anterior: dos cortes no, pero corte + barba sí. */
export function toggleService(categories: PublicCategory[], ids: string[], id: string): string[] {
  if (ids.includes(id)) return ids.filter((value) => value !== id);
  const category = categories.find((c) => c.services.some((service) => service.id === id));
  if (!category?.single_choice) return [...ids, id];
  const sameCategory = new Set(category.services.map((service) => service.id));
  return [...ids.filter((value) => !sameCategory.has(value)), id];
}
