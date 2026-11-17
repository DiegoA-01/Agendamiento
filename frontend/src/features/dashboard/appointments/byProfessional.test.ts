import { describe, expect, it } from "vitest";
import type { Appointment } from "../../../shared/api/types";
import { groupByProfessional } from "./byProfessional";

const appt = (id: string, professional_id: string, start_at: string) =>
  ({ id, professional_id, start_at }) as Appointment;

describe("citas por profesional", () => {
  it("agrupa en el orden del equipo, ordena por hora y omite a quien no tiene citas", () => {
    const groups = groupByProfessional(
      [
        appt("c", "camila", "2026-11-17T15:00:00-05:00"),
        appt("a2", "andres", "2026-11-17T11:00:00-05:00"),
        appt("a1", "andres", "2026-11-17T09:00:00-05:00"),
        appt("x", "ex", "2026-11-17T10:00:00-05:00"),
      ],
      [
        { id: "andres", display_name: "Andrés" },
        { id: "julian", display_name: "Julián" },
        { id: "camila", display_name: "Camila" },
      ],
      "Otro",
    );
    expect(groups.map((g) => [g.name, g.appointments.map((a) => a.id)])).toEqual([
      ["Andrés", ["a1", "a2"]],
      ["Camila", ["c"]],
      ["Otro", ["x"]],
    ]);
  });
});
