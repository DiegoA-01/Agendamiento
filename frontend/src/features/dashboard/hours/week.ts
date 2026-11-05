import type { WorkingHours } from "../../../shared/api/types";

/** Lunes a domingo, como la API (0 = lunes). */
export const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6] as const;

export interface Interval {
  start: string; // "HH:MM"
  end: string;
}
export type Week = Interval[][];

export type IntervalError = "required" | "endBeforeStart" | "overlap";

/** La API devuelve "09:00:00"; los campos de hora usan "09:00". */
function hhmm(time: string): string {
  return time.slice(0, 5);
}

export function emptyWeek(): Week {
  return WEEKDAYS.map(() => []);
}

export function weekFromHours(hours: WorkingHours[]): Week {
  const week = emptyWeek();
  for (const item of hours) {
    week[item.weekday]?.push({ start: hhmm(item.start_time), end: hhmm(item.end_time) });
  }
  for (const day of week) day.sort((a, b) => a.start.localeCompare(b.start));
  return week;
}

export function hoursFromWeek(week: Week): WorkingHours[] {
  return week.flatMap((day, weekday) =>
    [...day]
      .sort((a, b) => a.start.localeCompare(b.start))
      .map((interval) => ({ weekday, start_time: interval.start, end_time: interval.end })),
  );
}

/** Errores por día y franja (`errors[dia][franja]`). Una franja que choca con otra del mismo día
 *  se marca en las dos. El servidor valida lo mismo; esto avisa antes de enviar. */
export function validateWeek(week: Week): (IntervalError | null)[][] {
  return week.map((day) => {
    const errors: (IntervalError | null)[] = day.map((interval) => {
      if (!interval.start || !interval.end) return "required";
      if (interval.start >= interval.end) return "endBeforeStart";
      return null;
    });
    day.forEach((a, i) => {
      day.forEach((b, j) => {
        if (i < j && !errors[i] && !errors[j] && a.start < b.end && b.start < a.end) {
          errors[i] = "overlap";
          errors[j] = "overlap";
        }
      });
    });
    return errors;
  });
}

export function hasErrors(errors: (IntervalError | null)[][]): boolean {
  return errors.some((day) => day.some(Boolean));
}

/** Copia las franjas de un día a otros (por ejemplo, lunes → martes a viernes). */
export function copyDay(week: Week, from: number, to: readonly number[]): Week {
  return week.map((day, weekday) =>
    to.includes(weekday) ? week[from].map((interval) => ({ ...interval })) : day,
  );
}

/** Total semanal en minutos, para el resumen. */
export function weeklyMinutes(week: Week): number {
  return week.flat().reduce((total, { start, end }) => {
    if (!start || !end || start >= end) return total;
    const [sh, sm] = start.split(":").map(Number);
    const [eh, em] = end.split(":").map(Number);
    return total + (eh * 60 + em) - (sh * 60 + sm);
  }, 0);
}
