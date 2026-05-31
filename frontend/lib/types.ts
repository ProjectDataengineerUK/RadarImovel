export interface Property {
  id: string;
  bank_id: string;
  external_code: string;
  title: string | null;
  property_type: string;
  address: string | null;
  neighborhood: string | null;
  city: string;
  state: string;
  latitude: number | null;
  longitude: number | null;
  area_total: number | null;
  area_private: number | null;
  bedrooms: number | null;
  parking_spaces: number | null;
  appraisal_value: number | null;
  minimum_value: number;
  current_value: number;
  discount_percent: number | null;
  occupancy_status: string;
  sale_modality: string;
  edital_number: string | null;
  auction_date: string | null;
  official_url: string;
  risk_level: string | null;
  opportunity_score: number | null;
  status: string;
  first_seen_at: string;
  last_seen_at: string;
}

export interface PropertyChange {
  id: string;
  property_id: string;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  detected_at: string;
}

export interface Watchlist {
  id: string;
  user_id: string;
  state: string | null;
  city: string | null;
  max_price: number | null;
  min_discount: number | null;
  property_type: string | null;
  bank_id: string | null;
  active: boolean;
  created_at: string;
}

export interface Alert {
  id: string;
  user_id: string;
  property_id: string;
  channel: string;
  status: string;
  message: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface User {
  id: string;
  firebase_uid: string;
  telegram_connected: boolean;
  created_at: string;
}

export interface PaginatedResponse<T> {
  total: number;
  items: T[];
  offset: number;
  limit: number;
}

export interface PropertyFilters {
  state?: string;
  city?: string;
  max_price?: number;
  min_discount?: number;
  occupancy_status?: string;
  sale_modality?: string;
}
