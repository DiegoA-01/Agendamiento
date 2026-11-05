import { useQuery } from "@tanstack/react-query";
import { api } from "../../../shared/api/client";
import type {
  BusinessLocation,
  Category,
  Company,
  OfferedService,
  Professional,
  Service,
  Specialty,
  Workstation,
} from "../../../shared/api/types";

/** Claves de caché del catálogo: al guardar, se invalida la clave de lo que cambió. */
export const KEYS = {
  company: ["company"],
  locations: ["locations"],
  categories: ["categories"],
  services: ["services"],
  resources: ["resources"],
  specialties: ["specialties"],
  professionals: ["professionals"],
  offers: (professionalId: string) => ["professionals", professionalId, "services"],
} as const;

export const useCompany = () =>
  useQuery({ queryKey: KEYS.company, queryFn: () => api<Company>("/api/v1/company/") });

export const useLocations = () =>
  useQuery({
    queryKey: KEYS.locations,
    queryFn: () => api<BusinessLocation[]>("/api/v1/locations/"),
  });

export const useCategories = () =>
  useQuery({ queryKey: KEYS.categories, queryFn: () => api<Category[]>("/api/v1/categories/") });

export const useServices = () =>
  useQuery({ queryKey: KEYS.services, queryFn: () => api<Service[]>("/api/v1/services/") });

export const useResources = (enabled = true) =>
  useQuery({
    queryKey: KEYS.resources,
    queryFn: () => api<Workstation[]>("/api/v1/resources/"),
    enabled,
  });

export const useSpecialties = () =>
  useQuery({
    queryKey: KEYS.specialties,
    queryFn: () => api<Specialty[]>("/api/v1/specialties/"),
  });

export const useProfessionals = () =>
  useQuery({
    queryKey: KEYS.professionals,
    queryFn: () => api<Professional[]>("/api/v1/professionals/"),
  });

export const useOffers = (professionalId: string) =>
  useQuery({
    queryKey: KEYS.offers(professionalId),
    queryFn: () =>
      api<{ services: OfferedService[] }>(`/api/v1/professionals/${professionalId}/services/`),
  });
