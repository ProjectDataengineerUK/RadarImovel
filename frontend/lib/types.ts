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
  edital_url?: string | null;
  auctioneer_name?: string | null;
}

export interface Encumbrance {
  type: string;
  amount_approx: number | null;
  description: string;
}

export interface Edital {
  edital_number: string | null;
  auction_date_1st: string | null;
  auction_date_2nd: string | null;
  minimum_bid_1st: number | null;
  minimum_bid_2nd: number | null;
  appraisal_value: number | null;
  payment_modalities: string[];
  occupancy_detail: string | null;
  encumbrances: Encumbrance[];
  total_debt_estimate: number | null;
  registration_number: string | null;
  auctioneer_name: string | null;
  risk_flags: string[];
  risk_level: string | null;
  extraction_confidence: number | null;
  processing_status: string | null;
  processed_at: string | null;
}

export interface PropertyDetailResponse {
  property: Property;
  changes: PropertyChange[];
  edital_processed: boolean;
  edital: Edital | null;
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

export interface RiskIndicator {
  code: string;
  value: unknown;
  source: string;
  date_fetched: string;
  note: string | null;
}

export interface RiskScore {
  property_id: string;
  score_total: number;
  risk_level: "low" | "moderate" | "elevated" | "high" | "critical";
  score_juridico: number;
  score_fundiario: number;
  score_fiscal: number;
  score_ocupacao: number;
  score_socioeconomico: number;
  score_mercado: number;
  score_partial: boolean;
  indicators: Record<string, RiskIndicator>;
  sources_consulted: string[];
  calculation_version: string;
  calculated_at: string | null;
}

export interface RiskHeatmapFeature {
  type: "Feature";
  properties: {
    city: string;
    state: string;
    risk_avg: number;
    property_count: number;
    lat?: number;
    lng?: number;
  };
  geometry: unknown | null;
}

export interface RiskHeatmap {
  type: "FeatureCollection";
  features: RiskHeatmapFeature[];
}

export interface PropertyFilters {
  state?: string;
  city?: string;
  max_price?: number;
  min_discount?: number;
  occupancy_status?: string;
  sale_modality?: string;
}
