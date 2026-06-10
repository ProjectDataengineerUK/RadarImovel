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
    queryFn: () => api.get("/properties/", { params }).then((r) => r.data),
    staleTime: 60_000,
  });
}

export function useProperty(id: string) {
  return useQuery<PropertyDetailResponse>({
    queryKey: ["property", id],
    queryFn: () => api.get(`/properties/${id}/`).then((r) => r.data),
    enabled: !!id,
  });
}
