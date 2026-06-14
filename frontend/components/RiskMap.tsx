"use client";

import { useEffect, useRef } from "react";
import { setOptions, importLibrary } from "@googlemaps/js-api-loader";
import type { RiskHeatmapFeature } from "@/lib/types";

setOptions({
  key: process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY ?? "",
  v: "weekly",
});

function riskColor(avg: number): string {
  if (avg <= 20) return "#22c55e";
  if (avg <= 40) return "#eab308";
  if (avg <= 60) return "#f97316";
  if (avg <= 80) return "#ef4444";
  return "#18181b";
}

interface Props {
  features: RiskHeatmapFeature[];
}

export function RiskMap({ features }: Props) {
  const divRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const circlesRef = useRef<google.maps.Circle[]>([]);

  useEffect(() => {
    if (!divRef.current) return;
    let cancelled = false;

    const init = async () => {
      await importLibrary("maps");
      if (cancelled || !divRef.current) return;

      if (!mapRef.current) {
        mapRef.current = new google.maps.Map(divRef.current, {
          center: { lat: -15, lng: -50 },
          zoom: 4,
          mapTypeControl: false,
          streetViewControl: false,
        });
      }

      const map = mapRef.current;

      circlesRef.current.forEach((c) => c.setMap(null));
      circlesRef.current = [];

      const filtered = features.filter(
        (f) => f.properties.lat != null && f.properties.lng != null
      );

      const infoWindow = new google.maps.InfoWindow({});

      filtered.forEach((f) => {
        const baseRadius = 30000;
        const count = f.properties.property_count ?? 1;
        const radius = baseRadius + Math.min(count * 800, 80000);

        const circle = new google.maps.Circle({
          map,
          center: { lat: f.properties.lat!, lng: f.properties.lng! },
          radius,
          fillColor: riskColor(f.properties.risk_avg),
          fillOpacity: 0.6,
          strokeColor: riskColor(f.properties.risk_avg),
          strokeWeight: 1,
          strokeOpacity: 0.8,
          clickable: true,
        });
        circle.addListener("click", () => {
          infoWindow.setContent(
            `<div style="font-size:13px"><strong>${f.properties.city}/${f.properties.state}</strong><br/>
             Risco médio: <b>${f.properties.risk_avg}</b><br/>
             Imóveis: ${f.properties.property_count}</div>`
          );
          infoWindow.setPosition({ lat: f.properties.lat!, lng: f.properties.lng! });
          infoWindow.open(map);
        });
        circlesRef.current.push(circle);
      });
    };

    init();
    return () => { cancelled = true; };
  }, [features]);

  return <div ref={divRef} className="h-full w-full rounded-lg" />;
}
