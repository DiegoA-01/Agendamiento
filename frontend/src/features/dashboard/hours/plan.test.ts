import { describe, expect, it } from "vitest";
import {
  copyPlanDay,
  emptyPlan,
  planFromWeek,
  planHasErrors,
  suggestBreak,
  validatePlan,
  weekFromPlan,
  type Plan,
} from "./plan";
import { emptyWeek } from "./week";

describe("jornada con descansos", () => {
  it("dos franjas con un hueco son una jornada con un descanso, y vuelven a ser franjas", () => {
    const week = emptyWeek();
    week[0] = [
      { start: "14:00", end: "19:00" },
      { start: "09:00", end: "13:00" },
    ];
    const plan = planFromWeek(week);
    expect(plan[0]).toEqual({
      start: "09:00",
      end: "19:00",
      breaks: [{ start: "13:00", end: "14:00" }],
    });
    expect(plan[1]).toBeNull();
    expect(weekFromPlan(plan)[0]).toEqual([
      { start: "09:00", end: "13:00" },
      { start: "14:00", end: "19:00" },
    ]);
  });

  it("franjas que se cruzan se juntan: no inventa un descanso", () => {
    const week = emptyWeek();
    week[0] = [
      { start: "09:00", end: "19:00" },
      { start: "12:50", end: "13:50" },
    ];
    expect(planFromWeek(week)[0]).toEqual({ start: "09:00", end: "19:00", breaks: [] });
  });

  it("valida la jornada y que cada descanso quede adentro y sin cruzarse", () => {
    const plan: Plan = emptyPlan();
    plan[0] = {
      start: "09:00",
      end: "18:00",
      breaks: [
        { start: "12:00", end: "13:00" },
        { start: "12:30", end: "13:30" },
        { start: "17:30", end: "18:30" },
        { start: "15:00", end: "" },
      ],
    };
    plan[1] = { start: "18:00", end: "09:00", breaks: [] };
    const errors = validatePlan(plan);
    expect(errors[0]?.breaks).toEqual(["breakOverlap", "breakOverlap", "breakOutside", "required"]);
    expect(errors[1]?.day).toBe("endBeforeStart");
    expect(errors[2]).toBeNull();
    expect(planHasErrors(errors)).toBe(true);
    expect(planHasErrors(validatePlan(emptyPlan()))).toBe(false);
  });

  it("copia el lunes sin compartir referencias y sugiere un descanso que cabe", () => {
    const plan = emptyPlan();
    plan[0] = { start: "09:00", end: "18:00", breaks: [{ start: "13:00", end: "14:00" }] };
    const copied = copyPlanDay(plan, 0, [1, 2]);
    expect(copied[2]).toEqual(plan[0]);
    expect(copied[2]?.breaks[0]).not.toBe(plan[0]?.breaks[0]);
    expect(suggestBreak({ start: "09:00", end: "18:00", breaks: [] })).toEqual({
      start: "13:00",
      end: "14:00",
    });
    expect(suggestBreak({ start: "14:00", end: "20:00", breaks: [] })).toEqual({
      start: "16:30",
      end: "17:30",
    });
  });
});
