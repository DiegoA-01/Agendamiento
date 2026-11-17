import { WEEKDAYS, type Interval, type Week } from "./week";

/** Un día de trabajo como lo piensa el dueño: la jornada (desde, hasta) y sus descansos. La API
 *  guarda franjas; un descanso es el hueco entre dos franjas (9–13 y 14–18 = descanso de 13 a 14). */
export interface DayPlan {
  start: string; // "HH:MM"
  end: string;
  breaks: Interval[];
}
/** `null` = ese día no trabaja. */
export type Plan = (DayPlan | null)[];

export type DayError = "required" | "endBeforeStart";
export type BreakError = "required" | "endBeforeStart" | "breakOutside" | "breakOverlap";
export interface PlanDayErrors {
  day: DayError | null;
  breaks: (BreakError | null)[];
}

const byStart = (a: Interval, b: Interval) => a.start.localeCompare(b.start);

/** Franjas de la API → jornada y descansos. Las franjas que se cruzan se juntan (no hay descanso
 *  entre ellas); los huecos que quedan son los descansos. */
export function planFromWeek(week: Week): Plan {
  return week.map((day) => {
    const intervals = day.filter((i) => i.start && i.end && i.start < i.end).sort(byStart);
    if (intervals.length === 0) return null;
    const merged: Interval[] = [];
    for (const interval of intervals) {
      const last = merged.at(-1);
      if (last && interval.start <= last.end) {
        if (interval.end > last.end) last.end = interval.end;
      } else merged.push({ ...interval });
    }
    return {
      start: merged[0].start,
      end: merged[merged.length - 1].end,
      breaks: merged.slice(1).map((next, i) => ({ start: merged[i].end, end: next.start })),
    };
  });
}

/** Jornada y descansos → franjas para la API: la jornada partida por cada descanso. */
export function weekFromPlan(plan: Plan): Week {
  return plan.map((day) => {
    if (!day) return [];
    const intervals: Interval[] = [];
    let cursor = day.start;
    for (const pause of [...day.breaks].sort(byStart)) {
      if (pause.start > cursor) intervals.push({ start: cursor, end: pause.start });
      if (pause.end > cursor) cursor = pause.end;
    }
    if (day.end > cursor) intervals.push({ start: cursor, end: day.end });
    return intervals;
  });
}

/** Errores de cada día: la jornada y cada descanso (que debe quedar dentro de la jornada y no
 *  cruzarse con otro descanso). */
export function validatePlan(plan: Plan): (PlanDayErrors | null)[] {
  return plan.map((day) => {
    if (!day) return null;
    const dayError: DayError | null =
      !day.start || !day.end ? "required" : day.start >= day.end ? "endBeforeStart" : null;
    const breaks: (BreakError | null)[] = day.breaks.map((pause) => {
      if (!pause.start || !pause.end) return "required";
      if (pause.start >= pause.end) return "endBeforeStart";
      if (!dayError && (pause.start <= day.start || pause.end >= day.end)) return "breakOutside";
      return null;
    });
    day.breaks.forEach((a, i) => {
      day.breaks.forEach((b, j) => {
        if (i < j && !breaks[i] && !breaks[j] && a.start < b.end && b.start < a.end) {
          breaks[i] = "breakOverlap";
          breaks[j] = "breakOverlap";
        }
      });
    });
    return { day: dayError, breaks };
  });
}

export function planHasErrors(errors: (PlanDayErrors | null)[]): boolean {
  return errors.some((day) => day !== null && (day.day !== null || day.breaks.some(Boolean)));
}

/** Copia la jornada y los descansos de un día a otros (lunes → martes a viernes). */
export function copyPlanDay(plan: Plan, from: number, to: readonly number[]): Plan {
  const source = plan[from];
  return plan.map((day, weekday) =>
    to.includes(weekday)
      ? source && { ...source, breaks: source.breaks.map((pause) => ({ ...pause })) }
      : day,
  );
}

/** Un descanso sugerido: de 13:00 a 14:00 si cabe; si no, una hora a mitad de la jornada. */
export function suggestBreak(day: DayPlan): Interval {
  if (day.start < "13:00" && day.end > "14:00") return { start: "13:00", end: "14:00" };
  const minutes = (time: string) => Number(time.slice(0, 2)) * 60 + Number(time.slice(3, 5));
  const mid = Math.floor((minutes(day.start) + minutes(day.end)) / 2 / 15) * 15;
  const fmt = (m: number) =>
    `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
  return { start: fmt(mid - 30), end: fmt(mid + 30) };
}

export function emptyPlan(): Plan {
  return WEEKDAYS.map(() => null);
}
