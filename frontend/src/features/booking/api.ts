import { useQuery } from "@tanstack/react-query";
import { api } from "../../shared/api/client";
import type {
  PublicAppointment,
  PublicCategory,
  PublicCompany,
  PublicProfessional,
  Slot,
} from "../../shared/api/types";

/** Peticiones de la reserva pública: sin sesión, el negocio sale del host. */
function serviceParams(serviceIds: string[], professionalId: string | null): URLSearchParams {
  const params = new URLSearchParams();
  for (const id of serviceIds) params.append("service_ids", id);
  if (professionalId) params.set("professional_id", professionalId);
  return params;
}

export const usePublicCompany = () =>
  useQuery({
    queryKey: ["public", "company"],
    queryFn: () => api<PublicCompany>("/api/v1/public/company/"),
    staleTime: 5 * 60 * 1000,
  });

export const usePublicServices = () =>
  useQuery({
    queryKey: ["public", "services"],
    queryFn: () => api<PublicCategory[]>("/api/v1/public/services/"),
  });

export const usePublicProfessionals = (serviceIds: string[]) =>
  useQuery({
    queryKey: ["public", "professionals", serviceIds],
    queryFn: () =>
      api<PublicProfessional[]>(`/api/v1/public/professionals/?${serviceParams(serviceIds, null)}`),
    enabled: serviceIds.length > 0,
  });

export const useAvailableDays = (
  serviceIds: string[],
  professionalId: string | null,
  month: string,
) =>
  useQuery({
    queryKey: ["public", "days", serviceIds, professionalId, month],
    queryFn: () => {
      const params = serviceParams(serviceIds, professionalId);
      params.set("month", month);
      return api<{ days: string[] }>(`/api/v1/public/availability/days/?${params}`);
    },
    enabled: serviceIds.length > 0 && Boolean(month),
  });

export const useSlots = (serviceIds: string[], professionalId: string | null, date: string) =>
  useQuery({
    queryKey: ["public", "slots", serviceIds, professionalId, date],
    queryFn: () => {
      const params = serviceParams(serviceIds, professionalId);
      params.set("date", date);
      return api<Slot[]>(`/api/v1/public/availability/slots/?${params}`);
    },
    enabled: serviceIds.length > 0 && Boolean(date),
  });

export const usePublicAppointment = (token: string) =>
  useQuery({
    queryKey: ["public", "appointment", token],
    queryFn: () =>
      api<PublicAppointment>(`/api/v1/public/appointments/${encodeURIComponent(token)}/`),
  });
