"use client";

import { useEffect, useRef } from "react";
import type { RiskHeatmapFeature } from "@/lib/types";

const RISK_COLORS: Record<string, string> = {
  low: "#22c55e",
  moderate: "#eab308",
  elevated: "#f97316",
  high: "#ef4444",
  critical: "#18181b",
};

function riskColor(avg: number): string {
  if (avg <= 20) return RISK_COLORS.low;
  if (avg <= 40) return RISK_COLORS.moderate;
  if (avg <= 60) return RISK_COLORS.elevated;
  if (avg <= 80) return RISK_COLORS.high;
  return RISK_COLORS.critical;
}

interface Props {
  features: RiskHeatmapFeature[];
}

export function RiskMap({ features }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window === "undefined" || !mapRef.current) return;

    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const L = require("leaflet");
    require("leaflet.heat");

    const map = L.map(mapRef.current).setView([-15, -50], 4);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
    }).addTo(map);

    const heatPoints = features
      .filter((f) => f.properties.lat != null && f.properties.lng != null)
      .map((f) => [f.properties.lat!, f.properties.lng!, f.properties.risk_avg / 100]);

    if (heatPoints.length > 0) {
      L.heatLayer(heatPoints, { radius: 35, blur: 20, maxZoom: 10 }).addTo(map);
    }

    features.forEach((f) => {
      if (f.properties.lat == null || f.properties.lng == null) return;
      L.circleMarker([f.properties.lat, f.properties.lng], {
        radius: 6,
        color: riskColor(f.properties.risk_avg),
        fillColor: riskColor(f.properties.risk_avg),
        fillOpacity: 0.8,
        weight: 1,
      })
        .bindPopup(
          `<strong>${f.properties.city}/${f.properties.state}</strong><br/>
           Risco médio: ${f.properties.risk_avg}<br/>
           Imóveis: ${f.properties.property_count}`
        )
        .addTo(map);
    });

    return () => {
      map.remove();
    };
  }, [features]);

  return <div ref={mapRef} className="h-full w-full rounded-lg" />;
}
