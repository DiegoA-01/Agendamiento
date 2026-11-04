import type { Me, PermissionResource } from "../../../shared/api/types";
import { useMe } from "../../auth/useMe";

/** Si los permisos de `/me/` incluyen la acción. Solo guía a la interfaz: la API valida igual. */
export function can(
  me: Pick<Me, "permissions"> | undefined,
  resource: PermissionResource,
  action: string,
): boolean {
  return Boolean(me?.permissions[resource]?.actions.includes(action));
}

export function useCan(resource: PermissionResource, action: string): boolean {
  return can(useMe().data, resource, action);
}
