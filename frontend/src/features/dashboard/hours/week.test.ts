import { describe, expect, it } from "vitest";
import {
  copyDay,
  emptyWeek,
  hasErrors,
  hoursFromWeek,
  validateWeek,
  weekFromHours,
  weeklyMinutes,
} from "./week";

describe("semana de trabajo", () => {
  it("convierte lo que manda la API y lo devuelve igual (con descanso)", () => {
    const week = weekFromHours([
      { weekday: 0, start_time: "14:00:00", end_time: "19:00:00" },
      { weekday: 0, start_time: "09:00:00", end_time: "13:00:00" },
      { weekday: 5, start_time: "09:00:00", end_time: "14:00:00" },
    ]);
    expect(week[0]).toEqual([
      { start: "09:00", end: "13:00" },
      { start: "14:00", end: "19:00" },
    ]);
    expect(week[1]).toEqual([]);
    expect(hoursFromWeek(week)).toEqual([
      { weekday: 0, start_time: "09:00", end_time: "13:00" },
      { weekday: 0, start_time: "14:00", end_time: "19:00" },
      { weekday: 5, start_time: "09:00", end_time: "14:00" },
    ]);
  });

  it("marca franjas vacías, al revés o que se cruzan", () => {
    const week = emptyWeek();
    week[0] = [
      { start: "09:00", end: "13:00" },
      { start: "12:00", end: "15:00" },
      { start: "16:00", end: "17:00" },
    ];
    week[1] = [{ start: "18:00", end: "09:00" }];
    week[2] = [{ start: "", end: "10:00" }];
    const errors = validateWeek(week);
    expect(errors[0]).toEqual(["overlap", "overlap", null]);
    expect(errors[1]).toEqual(["endBeforeStart"]);
    expect(errors[2]).toEqual(["required"]);
    expect(hasErrors(errors)).toBe(true);
  });

  it("franjas seguidas no se cruzan", () => {
    const week = emptyWeek();
    week[0] = [
      { start: "09:00", end: "13:00" },
      { start: "13:00", end: "18:00" },
    ];
    expect(hasErrors(validateWeek(week))).toBe(false);
  });

  it("copia un día a otros sin compartir referencias", () => {
    const week = emptyWeek();
    week[0] = [{ start: "09:00", end: "18:00" }];
    const copied = copyDay(week, 0, [1, 2, 3, 4]);
    expect(copied.slice(0, 6).map((day) => day.length)).toEqual([1, 1, 1, 1, 1, 0]);
    copied[1][0].start = "10:00";
    expect(copied[0][0].start).toBe("09:00");
  });

  it("suma las horas de la semana", () => {
    const week = emptyWeek();
    week[0] = [
      { start: "09:00", end: "13:00" },
      { start: "14:00", end: "18:30" },
    ];
    expect(weeklyMinutes(week)).toBe(8 * 60 + 30);
  });
});
