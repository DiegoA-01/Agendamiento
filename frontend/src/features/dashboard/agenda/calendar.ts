import type { Appointment } from "../../../shared/api/types";
import { todayIn } from "../../booking/wizard";

export function addDays(date: string, delta: number): string {
  const value = new Date(`${date}T12:00:00Z`);
  value.setUTCDate(value.getUTCDate() + delta);
  return value.toISOString().slice(0, 10);
}
export function weekDays(date: string): string[] {
  const weekday = (new Date(`${date}T12:00:00Z`).getUTCDay() + 6) % 7;
  return Array.from({ length: 7 }, (_, index) => addDays(date, index - weekday));
}
export function defaultRange(timeZone: string, now = new Date()) {
  const from = todayIn(timeZone, now);
  return { from, to: addDays(from, 6) };
}
export function dateFilters(from: string, to: string) {
  return { start_at: `${from}T00:00`, end_at: `${addDays(to, 1)}T00:00` };
}
export function localMinutes(iso: string, timeZone: string): number {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(iso));
  return (
    Number(parts.find((p) => p.type === "hour")?.value) * 60 +
    Number(parts.find((p) => p.type === "minute")?.value)
  );
}
/** Cada minuto ocupa un píxel; los bloques se recortan al día visible. */
export function blockPosition(
  appointment: Pick<Appointment, "start_at" | "end_at">,
  date: string,
  timeZone: string,
) {
  const startDay = todayIn(timeZone, new Date(appointment.start_at));
  const endDay = todayIn(timeZone, new Date(appointment.end_at));
  const top = startDay < date ? 0 : localMinutes(appointment.start_at, timeZone);
  const end = endDay > date ? 1440 : localMinutes(appointment.end_at, timeZone);
  return { top, height: Math.max(1, end - top) };
}
export function groupAppointments(
  appointments: Appointment[],
  dates: string[],
  professionalIds: string[],
  timeZone: string,
) {
  return dates.map((date) => ({
    date,
    professionals: professionalIds.map((id) => ({
      id,
      appointments: appointments.filter(
        (a) =>
          a.professional_id === id &&
          todayIn(timeZone, new Date(a.start_at)) <= date &&
          (todayIn(timeZone, new Date(a.end_at)) > date ||
            (todayIn(timeZone, new Date(a.end_at)) === date &&
              localMinutes(a.end_at, timeZone) > 0)),
      ),
    })),
  }));
}

/** Asigna carriles estables dentro de cada grupo de citas que se cruzan. */
export function layoutBlocks(appointments: Appointment[], date: string, timeZone: string) {
  const sorted = appointments
    .map((appointment) => ({ appointment, ...blockPosition(appointment, date, timeZone) }))
    .sort((a, b) => a.top - b.top || b.height - a.height);
  const result: {
    appointment: Appointment;
    top: number;
    height: number;
    left: number;
    width: number;
  }[] = [];
  let index = 0;
  while (index < sorted.length) {
    let end = sorted[index].top + sorted[index].height;
    const group = [];
    do {
      const block = sorted[index++];
      group.push(block);
      end = Math.max(end, block.top + block.height);
    } while (index < sorted.length && sorted[index].top < end);
    const laneEnds: number[] = [];
    const assigned = group.map((block) => {
      let lane = laneEnds.findIndex((value) => value <= block.top);
      if (lane < 0) lane = laneEnds.length;
      laneEnds[lane] = block.top + block.height;
      return { ...block, lane };
    });
    result.push(
      ...assigned.map(({ lane, ...block }) => ({
        ...block,
        left: (lane * 100) / laneEnds.length,
        width: 100 / laneEnds.length,
      })),
    );
  }
  return result;
}
