import type { Me, ModuleKey, PermissionResource } from "../../shared/api/types";

export type DashboardSection =
  | "home"
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
  /** Recurso de la matriz que hay que poder ver para que aparezca el enlace. */
  resource: PermissionResource;
  /** Si es `true`, hace falta verlo todo: quien solo ve lo propio no recibe el enlace. */
  allRecords?: boolean;
  /** Si se indica, basta con que el negocio tenga habilitado uno de estos módulos. */
  modules?: readonly ModuleKey[];
}

/** Secciones del panel, en el orden del menú. Quién ve cada una sale de los permisos que manda
 *  `/me/` (la misma matriz con la que el backend valida); esto solo evita mostrar enlaces que
 *  darían 403. */
export const DASHBOARD_LINKS: readonly DashboardLink[] = [
  // Resumen del negocio: ventas y citas de todo el negocio, así que solo para quien lo ve todo.
  {
    section: "home",
    path: "/inicio",
    resource: "commissions",
    allRecords: true,
    modules: ["reports", "commissions"],
  },
  { section: "agenda", path: "/agenda", resource: "appointments", modules: ["booking"] },
  { section: "appointments", path: "/citas", resource: "appointments", modules: ["booking"] },
  {
    section: "customers",
    path: "/clientes",
    resource: "appointments",
    allRecords: true,
    modules: ["booking"],
  },
  { section: "services", path: "/servicios", resource: "staff_services" },
  { section: "team", path: "/equipo", resource: "staff_services" },
  { section: "resources", path: "/puestos", resource: "staff_services", allRecords: true },
  { section: "hours", path: "/horarios", resource: "schedules" },
  {
    section: "reports",
    path: "/reportes",
    resource: "commissions",
    modules: ["reports", "commissions"],
  },
  { section: "company", path: "/empresa", resource: "company" },
];

export function canSee(me: Pick<Me, "permissions" | "modules">, link: DashboardLink): boolean {
  const grant = me.permissions[link.resource];
  if (!grant?.actions.includes("view")) return false;
  if (link.allRecords && grant.scope !== "all") return false;
  return !link.modules || link.modules.some((key) => me.modules.includes(key));
}

export function visibleLinks(me: Pick<Me, "permissions" | "modules">): DashboardLink[] {
  return DASHBOARD_LINKS.filter((link) => canSee(me, link));
}
