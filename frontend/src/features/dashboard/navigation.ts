import type { Me, ModuleKey, Role } from "../../shared/api/types";

export type DashboardSection =
  | "agenda"
  | "appointments"
  | "customers"
  | "services"
  | "team"
  | "resources"
  | "hours"
  | "reports"
  | "company";

export interface DashboardLink {
  section: DashboardSection;
  /** Ruta de la spec §13 (en español, como la ve el usuario). */
  path: string;
  roles: readonly Role[];
  /** Si se indica, basta con que el negocio tenga habilitado uno de estos módulos. */
  modules?: readonly ModuleKey[];
}

const STAFF: readonly Role[] = ["owner", "admin", "receptionist", "professional"];

/** Secciones del panel, en el orden del menú. Quién ve cada una sale de la matriz de la spec §5;
 *  el backend vuelve a validar todo, esto solo evita mostrar enlaces que darían 403. */
export const DASHBOARD_LINKS: readonly DashboardLink[] = [
  { section: "agenda", path: "/agenda", roles: STAFF, modules: ["booking"] },
  { section: "appointments", path: "/citas", roles: STAFF, modules: ["booking"] },
  {
    section: "customers",
    path: "/clientes",
    roles: ["owner", "admin", "receptionist"],
    modules: ["booking"],
  },
  { section: "services", path: "/servicios", roles: STAFF },
  { section: "team", path: "/equipo", roles: STAFF },
  { section: "resources", path: "/puestos", roles: ["owner", "admin", "receptionist"] },
  { section: "hours", path: "/horarios", roles: STAFF },
  {
    section: "reports",
    path: "/reportes",
    roles: ["owner", "admin", "professional"],
    modules: ["reports", "commissions"],
  },
  { section: "company", path: "/empresa", roles: ["owner", "admin"] },
];

export function canSee(me: Pick<Me, "role" | "modules">, link: DashboardLink): boolean {
  if (!link.roles.includes(me.role)) return false;
  return !link.modules || link.modules.some((key) => me.modules.includes(key));
}

export function visibleLinks(me: Pick<Me, "role" | "modules">): DashboardLink[] {
  return DASHBOARD_LINKS.filter((link) => canSee(me, link));
}
