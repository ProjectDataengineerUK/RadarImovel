"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  PaginatedResponse,
  Property,
  PropertyDetailResponse,
  PropertyFilters,
} from "@/lib/types";

export function useProperties(filters: PropertyFilters = {}, page = 0, limit = 50) {
  const params = {
    ...filters,
    offset: page * limit,
    limit,
  };

  return useQuery<PaginatedResponse<Property>>({
    queryKey: ["properties", params],
    queryFn: () => api.get("/properties", { params }).then((r) => r.data),
    staleTime: 60_000,
  });
}

export function useProperty(id: string) {
  return useQuery<PropertyDetailResponse>({
    queryKey: ["property", id],
    queryFn: () => api.get(`/properties/${id}`).then((r) => r.data),
    enabled: !!id,
  });
}

export interface PropertyOffer {
  id: string;
  source_name: string;
  price: number;
  modality: string;
  auction_date: string | null;
  official_url: string;
}

export function usePropertyOffers(id: string) {
  return useQuery<PropertyOffer[]>({
    queryKey: ["property", id, "offers"],
    queryFn: () => api.get(`/properties/${id}/offers`).then((r) => r.data),
    enabled: !!id,
  });
}

export function usePropertyMatricula(id: string) {
  return useQuery({
    queryKey: ["property", id, "matricula"],
    queryFn: () => api.get(`/properties/${id}/matricula`).then((r) => r.data),
    enabled: !!id,
    retry: false,
  });
}
