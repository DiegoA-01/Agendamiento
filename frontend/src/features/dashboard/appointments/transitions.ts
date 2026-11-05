import type { AppointmentStatus } from "../../../shared/api/types";

export const TRANSITIONS = {
  confirm: ["pending"],
  start: ["confirmed"],
  complete: ["in_progress"],
  no_show: ["confirmed"],
  cancel: ["pending", "confirmed"],
  reschedule: ["pending", "confirmed"],
} as const;
export type AppointmentAction = keyof typeof TRANSITIONS;
export function allowedActions(status: AppointmentStatus): AppointmentAction[] {
  return (Object.keys(TRANSITIONS) as AppointmentAction[]).filter((action) =>
    (TRANSITIONS[action] as readonly AppointmentStatus[]).includes(status),
  );
}
export const STATUSES: AppointmentStatus[] = [
  "pending",
  "confirmed",
  "in_progress",
  "completed",
  "cancelled",
  "no_show",
  "rescheduled",
];
