import { describe, expect, it } from "vitest";
import { allowedActions } from "./transitions";

describe("appointment transitions", () => {
  it("permits only the spec transitions from active states", () => {
    expect(allowedActions("pending")).toEqual(["confirm", "cancel", "reschedule"]);
    expect(allowedActions("confirmed")).toEqual(["start", "no_show", "cancel", "reschedule"]);
    expect(allowedActions("in_progress")).toEqual(["complete"]);
  });
  it.each(["completed", "cancelled", "no_show", "rescheduled"] as const)(
    "makes %s terminal",
    (status) => {
      expect(allowedActions(status)).toEqual([]);
    },
  );
});
