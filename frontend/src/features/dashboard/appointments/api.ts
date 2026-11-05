import { useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, cursorFrom } from "../../../shared/api/client";
import type { Appointment, CustomerRecord, Paginated, Slot } from "../../../shared/api/types";
import { KEYS } from "../shared/api";

export type AppointmentFilters = {
  start_at?: string;
  end_at?: string;
  professional_id?: string;
  customer_id?: string;
  status?: string[];
};
export function appointmentParams(filters: AppointmentFilters): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (Array.isArray(value)) value.forEach((status) => params.append(key, status));
    else if (value) params.set(key, value);
  }
  return params;
}
export function useAppointments(filters: AppointmentFilters) {
  return useInfiniteQuery({
    queryKey: [...KEYS.appointments, filters],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => {
      const params = appointmentParams(filters);
      if (pageParam) params.set("cursor", pageParam);
      return api<Paginated<Appointment>>(`/api/v1/appointments/?${params}`);
    },
    getNextPageParam: (page) => cursorFrom(page.next),
  });
}
/** La grilla necesita todas las páginas del intervalo, no solo las primeras citas. */
export function useAgendaAppointments(filters: AppointmentFilters) {
  return useQuery({
    queryKey: [...KEYS.appointments, "grid", filters],
    queryFn: async () => {
      const results: Appointment[] = [];
      const params = appointmentParams(filters);
      let cursor: string | undefined;
      do {
        if (cursor) params.set("cursor", cursor);
        const page = await api<Paginated<Appointment>>(`/api/v1/appointments/?${params}`);
        results.push(...page.results);
        cursor = cursorFrom(page.next);
      } while (cursor);
      return results;
    },
  });
}
export function useCustomers(q: string, enabled = true) {
  return useInfiniteQuery({
    queryKey: [...KEYS.customers, q],
    enabled,
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams({ q });
      if (pageParam) params.set("cursor", pageParam);
      return api<Paginated<CustomerRecord>>(`/api/v1/customers/?${params}`);
    },
    getNextPageParam: (page) => cursorFrom(page.next),
  });
}
export function useSlots(serviceIds: string[], professionalId: string, date: string) {
  return useQuery({
    queryKey: [...KEYS.slots, serviceIds, professionalId, date],
    enabled: !!serviceIds.length && !!date,
    queryFn: () => {
      const params = new URLSearchParams({ service_ids: serviceIds.join(","), date });
      if (professionalId) params.set("professional_id", professionalId);
      return api<Slot[]>(`/api/v1/availability/slots/?${params}`);
    },
  });
}
export function useDebounced(value: string) {
  const [result, setResult] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setResult(value), 300);
    return () => window.clearTimeout(timer);
  }, [value]);
  return result;
}
export function useRefreshAppointments() {
  const client = useQueryClient();
  return () => {
    void client.invalidateQueries({ queryKey: KEYS.appointments });
    void client.invalidateQueries({ queryKey: KEYS.slots });
    void client.invalidateQueries({ queryKey: KEYS.customers });
  };
}
