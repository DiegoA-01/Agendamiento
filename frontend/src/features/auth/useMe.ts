import { useQuery } from "@tanstack/react-query";
import { api } from "../../shared/api/client";
import type { Me } from "../../shared/api/types";

export const ME_KEY = ["me"] as const;

/** Quién está en sesión. Un 401 no es un fallo: significa "nadie", y no se reintenta. */
export function useMe() {
  return useQuery({
    queryKey: ME_KEY,
    queryFn: () => api<Me>("/api/v1/me/"),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

export function homePathFor(me: Me): string {
  return me.is_platform_admin ? "/empresas" : "/panel";
}
