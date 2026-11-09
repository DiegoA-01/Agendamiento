import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, cursorFrom } from "../../../shared/api/client";
import type { Paginated } from "../../../shared/api/types";

/** Reportes y comisiones (spec §11). Las fechas son días locales del negocio, ambos incluidos. */
export type SalesGroup = "day" | "week" | "month" | "professional" | "service";
export const SALES_GROUPS: SalesGroup[] = ["day", "week", "month", "professional", "service"];

export interface ReportFilters {
  from: string;
  to: string;
  professional_id?: string;
}

export interface SalesMetrics {
  sales: string;
  commissions: string;
  business: string;
  appointments: number;
  average_ticket: string;
}

export interface SalesReport {
  from: string;
  to: string;
  group_by: SalesGroup;
  totals: SalesMetrics;
  rows: (SalesMetrics & { key: string; label: string })[];
}

export interface BookingMetrics {
  total: number;
  completed: number;
  cancelled: number;
  no_show: number;
  web: number;
  cancellation_rate: string;
  no_show_rate: string;
}

export type BookingRow = BookingMetrics & { key: string; label: string };

export interface BookingsReport {
  from: string;
  to: string;
  totals: BookingMetrics;
  by_month: BookingRow[];
  by_professional: BookingRow[];
  by_service: BookingRow[];
}

export interface CommissionEntry {
  id: string;
  kind: "entry" | "adjustment";
  appointment_id: string;
  appointment_start_at: string;
  professional_id: string;
  professional_name: string;
  service_id: string;
  service_name: string;
  base_amount: string;
  pct: string;
  commission_amount: string;
  business_amount: string;
  adjusts_id: string | null;
  reason: string;
  created_at: string;
}

export interface AdjustmentInput {
  base_amount: string;
  commission_amount: string;
  reason: string;
}

export function reportParams(filters: ReportFilters, extra: Record<string, string> = {}) {
  const params = new URLSearchParams({ from: filters.from, to: filters.to, ...extra });
  if (filters.professional_id) params.set("professional_id", filters.professional_id);
  return params;
}

/** Enlace de descarga del CSV: la sesión viaja en la cookie, no hace falta `fetch`. */
export function exportUrl(path: string, filters: ReportFilters, extra?: Record<string, string>) {
  return `/api/v1/${path}export/?${reportParams(filters, extra)}`;
}

const KEY = ["reports"] as const;

export const useSalesReport = (filters: ReportFilters, groupBy: SalesGroup, enabled = true) =>
  useQuery({
    queryKey: [...KEY, "sales", filters, groupBy],
    queryFn: () =>
      api<SalesReport>(`/api/v1/reports/sales/?${reportParams(filters, { group_by: groupBy })}`),
    enabled,
  });

export const useBookingsReport = (filters: ReportFilters, enabled = true) =>
  useQuery({
    queryKey: [...KEY, "bookings", filters],
    queryFn: () => api<BookingsReport>(`/api/v1/reports/bookings/?${reportParams(filters)}`),
    enabled,
  });

export const useCommissions = (filters: ReportFilters, enabled = true) =>
  useInfiniteQuery({
    queryKey: [...KEY, "commissions", filters],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => {
      const params = reportParams(filters);
      if (pageParam) params.set("cursor", pageParam);
      return api<Paginated<CommissionEntry>>(`/api/v1/commissions/?${params}`);
    },
    getNextPageParam: (page) => cursorFrom(page.next),
    enabled,
  });

export function useAdjustCommission() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: AdjustmentInput & { id: string }) =>
      api<CommissionEntry>(`/api/v1/commissions/${id}/adjustments/`, { method: "POST", body }),
    // Un ajuste cambia las comisiones y los totales de ventas.
    onSuccess: () => void client.invalidateQueries({ queryKey: KEY }),
  });
}
