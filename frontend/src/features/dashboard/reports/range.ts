/** Rangos de fechas de los reportes, en días locales del negocio (`YYYY-MM-DD`). */

export interface DateRange {
  from: string;
  to: string;
}

/** Hoy en la zona horaria del negocio, no en la del navegador. */
export function todayIn(timeZone: string, now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone }).format(now);
}

function lastDayOf(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

/** Del día 1 al último día del mes de `date`. */
export function monthRange(date: string): DateRange {
  const [year, month] = date.split("-").map(Number);
  const mm = String(month).padStart(2, "0");
  return { from: `${year}-${mm}-01`, to: `${year}-${mm}-${lastDayOf(year, month)}` };
}

/** El mes anterior completo al de `date`. */
export function previousMonthRange(date: string): DateRange {
  const [year, month] = date.split("-").map(Number);
  const prev = month === 1 ? { year: year - 1, month: 12 } : { year, month: month - 1 };
  return monthRange(`${prev.year}-${String(prev.month).padStart(2, "0")}-01`);
}

/** Los últimos 7 días, hoy incluido. */
export function lastSevenDays(date: string): DateRange {
  const day = new Date(`${date}T12:00:00Z`);
  day.setUTCDate(day.getUTCDate() - 6);
  return { from: day.toISOString().slice(0, 10), to: date };
}

/** El rango es válido si `from` ≤ `to` y no pasa de un año (el límite de la API). */
export function isValidRange({ from, to }: DateRange): boolean {
  if (!from || !to || from > to) return false;
  const days = (Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86_400_000;
  return days < 366;
}
