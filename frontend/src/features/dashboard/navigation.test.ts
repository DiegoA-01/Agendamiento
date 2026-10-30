import { describe, expect, it } from "vitest";
import type { ModuleKey, Role } from "../../shared/api/types";
import { visibleLinks } from "./navigation";

const ALL_MODULES: ModuleKey[] = ["booking", "commissions", "reports", "notifications_whatsapp"];

function paths(role: Role, modules: ModuleKey[] = ALL_MODULES) {
  return visibleLinks({ role, modules }).map((link) => link.path);
}

describe("menú del panel según rol (spec §5)", () => {
  it.each<[Role, string[]]>([
    [
      "owner",
      [
        "/agenda",
        "/citas",
        "/clientes",
        "/servicios",
        "/equipo",
        "/puestos",
        "/horarios",
        "/reportes",
        "/empresa",
      ],
    ],
    [
      "admin",
      [
        "/agenda",
        "/citas",
        "/clientes",
        "/servicios",
        "/equipo",
        "/puestos",
        "/horarios",
        "/reportes",
        "/empresa",
      ],
    ],
    [
      "receptionist",
      ["/agenda", "/citas", "/clientes", "/servicios", "/equipo", "/puestos", "/horarios"],
    ],
    ["professional", ["/agenda", "/citas", "/servicios", "/equipo", "/horarios", "/reportes"]],
    ["superadmin", []],
  ])("%s", (role, expected) => {
    expect(paths(role)).toEqual(expected);
  });
});

describe("menú del panel según módulos", () => {
  it("sin el módulo de reservas no muestra agenda, citas ni clientes", () => {
    expect(paths("owner", ["reports"])).toEqual([
      "/servicios",
      "/equipo",
      "/puestos",
      "/horarios",
      "/reportes",
      "/empresa",
    ]);
  });

  it("reportes aparece con el módulo de reportes o con el de comisiones", () => {
    expect(paths("owner", [])).not.toContain("/reportes");
    expect(paths("owner", ["reports"])).toContain("/reportes");
    expect(paths("professional", ["commissions"])).toContain("/reportes");
  });
});
