import { describe, expect, it } from "vitest";
import type { ModuleKey, Permissions, Role } from "../../shared/api/types";
import { visibleLinks } from "./navigation";

const ALL_MODULES: ModuleKey[] = ["booking", "commissions", "reports", "notifications_whatsapp"];

const CRUD = ["create", "delete", "update", "view"];
const APPOINTMENT_ACTIONS = [
  ...CRUD,
  "cancel",
  "complete",
  "confirm",
  "no_show",
  "reschedule",
  "start",
];

// Lo que devuelve `/me/` para cada rol (copia de `accounts/permissions.py`, solo para la prueba).
const PERMISSIONS: Record<Role, Permissions> = {
  owner: {
    company: { scope: "all", actions: ["update", "view"] },
    staff_services: { scope: "all", actions: CRUD },
    schedules: { scope: "all", actions: CRUD },
    appointments: { scope: "all", actions: APPOINTMENT_ACTIONS },
    commissions: { scope: "all", actions: ["view"] },
    plan_modules: { scope: "all", actions: ["view"] },
  },
  admin: {
    company: { scope: "all", actions: ["view"] },
    staff_services: { scope: "all", actions: CRUD },
    schedules: { scope: "all", actions: CRUD },
    appointments: { scope: "all", actions: APPOINTMENT_ACTIONS },
    commissions: { scope: "all", actions: ["view"] },
  },
  receptionist: {
    staff_services: { scope: "all", actions: ["view"] },
    schedules: { scope: "all", actions: CRUD },
    appointments: { scope: "all", actions: APPOINTMENT_ACTIONS },
  },
  professional: {
    staff_services: { scope: "own", actions: ["view"] },
    schedules: { scope: "own", actions: CRUD },
    appointments: { scope: "own", actions: ["complete", "no_show", "view"] },
    commissions: { scope: "own", actions: ["view"] },
  },
  superadmin: { platform: { scope: "all", actions: CRUD } },
};

function paths(role: Role, modules: ModuleKey[] = ALL_MODULES) {
  return visibleLinks({ permissions: PERMISSIONS[role], modules }).map((link) => link.path);
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

describe("menú del panel según los permisos que manda /me/", () => {
  it("si el backend quita un permiso, el menú oculta la sección sin tocar el frontend", () => {
    const withoutCommissions = { ...PERMISSIONS.professional };
    delete withoutCommissions.commissions;
    const links = visibleLinks({ permissions: withoutCommissions, modules: ALL_MODULES });
    expect(links.map((link) => link.path)).not.toContain("/reportes");
  });

  it("una sección que exige ver todo no aparece a quien solo ve lo propio", () => {
    const links = visibleLinks({ permissions: PERMISSIONS.professional, modules: ALL_MODULES });
    expect(links.map((link) => link.path)).not.toContain("/clientes");
    expect(links.map((link) => link.path)).not.toContain("/puestos");
  });
});
