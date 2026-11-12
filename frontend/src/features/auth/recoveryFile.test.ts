import { describe, expect, it } from "vitest";
import { recoveryCodesText } from "./recoveryFile";

describe("archivo de códigos de recuperación (pormejorar §2)", () => {
  it("lista los códigos numerados con el correo, la fecha y la nota", () => {
    const text = recoveryCodesText(["abcde-23456", "fghjk-789ab"], {
      title: "Códigos de recuperación de Agenda",
      note: "Cada código sirve una sola vez.",
      email: "root@demo.com",
      issuedAt: new Date("2026-11-11T15:00:00Z"),
    });
    expect(text.split("\n")).toEqual([
      "Códigos de recuperación de Agenda",
      "root@demo.com",
      "2026-11-11",
      "",
      "1. abcde-23456",
      "2. fghjk-789ab",
      "",
      "Cada código sirve una sola vez.",
      "",
    ]);
  });
});
