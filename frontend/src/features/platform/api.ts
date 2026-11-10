import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { api, cursorFrom } from "../../shared/api/client";
import type {
  AuditEntry,
  Domain,
  ModulesInfo,
  Paginated,
  Plan,
  Tenant,
  TenantDetail,
  TenantIntegrations,
} from "../../shared/api/types";

export function queryString(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value);
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export const usePlans = () =>
  useQuery({ queryKey: ["plans"], queryFn: () => api<Plan[]>("/api/v1/plans/") });

export const useTenant = (id: string) =>
  useQuery({
    queryKey: ["tenant", id],
    queryFn: () => api<TenantDetail>(`/api/v1/tenants/${id}/`),
  });

/** Uso del sistema por negocio (S10). `*_recent`: citas creadas en los últimos `window_days`. */
export interface TenantUsage {
  window_days: number;
  appointments_total: number;
  appointments_recent: number;
  web_bookings_recent: number;
  completed_recent: number;
  cancelled_recent: number;
  customers_total: number;
  users_active: number;
  last_login: string | null;
}

export const useTenantUsage = (id: string) =>
  useQuery({
    queryKey: ["tenant", id, "usage"],
    queryFn: () => api<TenantUsage>(`/api/v1/tenants/${id}/usage/`),
  });

export const useTenantModules = (id: string) =>
  useQuery({
    queryKey: ["tenant", id, "modules"],
    queryFn: () => api<ModulesInfo>(`/api/v1/tenants/${id}/modules/`),
  });

export const useTenantDomains = (id: string) =>
  useQuery({
    queryKey: ["tenant", id, "domains"],
    queryFn: () => api<Domain[]>(`/api/v1/tenants/${id}/domains/`),
  });

export function useTenantList(filters: { q: string; status: string }) {
  return useInfiniteQuery({
    queryKey: ["tenants", filters],
    queryFn: ({ pageParam }) =>
      api<Paginated<Tenant>>(`/api/v1/tenants/${queryString({ ...filters, cursor: pageParam })}`),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => cursorFrom(last.next),
  });
}

export function useAuditList(filters: { action: string }) {
  return useInfiniteQuery({
    queryKey: ["audit", filters],
    queryFn: ({ pageParam }) =>
      api<Paginated<AuditEntry>>(
        `/api/v1/audit-log/${queryString({ ...filters, cursor: pageParam })}`,
      ),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => cursorFrom(last.next),
  });
}

export const AUDIT_ACTIONS = [
  "tenant.create",
  "tenant.update",
  "tenant.suspend",
  "tenant.activate",
  "tenant.delete",
  "tenant.theme",
  "tenant.modules",
  "domain.add",
  "domain.verify",
  "domain.remove",
  "plan.create",
  "plan.update",
  "plan.delete",
  "auth.login",
  "auth.login_failed",
  "auth.password_change",
  "auth.password_reset_request",
  "auth.password_reset",
  "auth.two_factor_enable",
  "auth.two_factor_reset",
] as const;

export const useTenantIntegrations = (id: string) =>
  useQuery({
    queryKey: ["tenant", id, "integrations"],
    queryFn: () => api<TenantIntegrations>(`/api/v1/tenants/${id}/integrations/`),
  });
