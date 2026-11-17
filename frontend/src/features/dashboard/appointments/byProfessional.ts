import type { Appointment, Professional } from "../../../shared/api/types";

export interface ProfessionalGroup {
  id: string;
  name: string;
  appointments: Appointment[];
}

/** Agrupa las citas por profesional, en el orden del equipo, y cada grupo por hora. Los grupos
 *  sin citas no salen. Si llega una cita de alguien que ya no está en el equipo, va al final con
 *  el nombre de respaldo. */
export function groupByProfessional(
  appointments: Appointment[],
  professionals: Pick<Professional, "id" | "display_name">[],
  unknownName: string,
): ProfessionalGroup[] {
  const byId = new Map<string, Appointment[]>();
  for (const appointment of appointments) {
    const list = byId.get(appointment.professional_id) ?? [];
    list.push(appointment);
    byId.set(appointment.professional_id, list);
  }
  const sortByStart = (list: Appointment[]) =>
    [...list].sort((a, b) => a.start_at.localeCompare(b.start_at));
  const groups: ProfessionalGroup[] = [];
  for (const professional of professionals) {
    const list = byId.get(professional.id);
    if (!list) continue;
    groups.push({
      id: professional.id,
      name: professional.display_name,
      appointments: sortByStart(list),
    });
    byId.delete(professional.id);
  }
  for (const [id, list] of byId) {
    groups.push({ id, name: unknownName, appointments: sortByStart(list) });
  }
  return groups;
}
