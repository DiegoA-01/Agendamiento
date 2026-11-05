import { describe, expect, it } from "vitest";
import type { Appointment } from "../../../shared/api/types";
import {
  layoutBlocks,
  addDays,
  blockPosition,
  dateFilters,
  defaultRange,
  groupAppointments,
  weekDays,
} from "./calendar";

describe("business calendar", () => {
  it("uses business today and includes seven calendar dates across month boundaries", () => {
    expect(defaultRange("America/Bogota", new Date("2026-11-01T02:00:00Z"))).toEqual({
      from: "2026-10-31",
      to: "2026-11-06",
    });
    expect(dateFilters("2026-10-31", "2026-11-06")).toEqual({
      start_at: "2026-10-31T00:00",
      end_at: "2026-11-07T00:00",
    });
    expect(addDays("2028-02-28", 1)).toBe("2028-02-29");
  });
  it("builds Monday to Sunday for Sunday and across years", () => {
    expect(weekDays("2027-01-03")).toEqual([
      "2026-12-28",
      "2026-12-29",
      "2026-12-30",
      "2026-12-31",
      "2027-01-01",
      "2027-01-02",
      "2027-01-03",
    ]);
  });
  it("positions according to business hours instead of UTC or browser zone", () => {
    expect(
      blockPosition(
        { start_at: "2026-11-09T15:15:00Z", end_at: "2026-11-09T16:00:00Z" },
        "2026-11-09",
        "America/Bogota",
      ),
    ).toEqual({ top: 615, height: 45 });
  });
  it("clips appointments crossing midnight", () => {
    const a = { start_at: "2026-11-09T23:30:00-05:00", end_at: "2026-11-10T00:30:00-05:00" };
    expect(blockPosition(a, "2026-11-09", "America/Bogota")).toEqual({ top: 1410, height: 30 });
    expect(blockPosition(a, "2026-11-10", "America/Bogota")).toEqual({ top: 0, height: 30 });
  });
  it("groups by local day and professional, including empty columns", () => {
    const a = {
      id: "a",
      professional_id: "p1",
      start_at: "2026-11-10T02:00:00Z",
      end_at: "2026-11-10T03:00:00Z",
    } as Appointment;
    const groups = groupAppointments(
      [a],
      ["2026-11-09", "2026-11-10"],
      ["p1", "p2"],
      "America/Bogota",
    );
    expect(groups[0].professionals[0].appointments).toEqual([a]);
    expect(groups[0].professionals[1].appointments).toEqual([]);
    expect(groups[1].professionals[0].appointments).toEqual([]);
  });
});

describe("overlapping blocks", () => {
  it("keeps chain overlaps in consistent lanes without hiding appointments", () => {
    const appointments = [
      [9, 11],
      [10, 12],
      [11, 13],
    ].map(
      ([start, end], index) =>
        ({
          id: String(index),
          start_at: `2026-11-09T${String(start).padStart(2, "0")}:00:00-05:00`,
          end_at: `2026-11-09T${String(end).padStart(2, "0")}:00:00-05:00`,
        }) as Appointment,
    );
    const blocks = layoutBlocks(appointments, "2026-11-09", "America/Bogota");
    expect(blocks.map((b) => [b.left, b.width])).toEqual([
      [0, 50],
      [50, 50],
      [0, 50],
    ]);
    expect(blocks.map((b) => b.height)).toEqual([120, 120, 120]);
  });
});
