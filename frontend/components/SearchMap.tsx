"use client";

import { useEffect, useRef, useState } from "react";
import type { Property } from "@/lib/types";

interface Props {
  properties: Property[];
  center: [number, number] | null;
  onCenterChange: (c: [number, number]) => void;
  radiusKm: number;
}

export default function SearchMap({ properties, center, radiusKm }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMap = useRef<unknown>(null);
  const clusterLayer = useRef<unknown>(null);
  const [selected, setSelected] = useState<Property | null>(null);

  useEffect(() => {
    if (typeof window === "undefined" || !mapRef.current) return;

    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const L = require("leaflet");
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    require("leaflet.markercluster");

    if (leafletMap.current) {
      (leafletMap.current as { remove: () => void }).remove();
    }

    const map = L.map(mapRef.current).setView(center ?? [-15, -50], center ? 11 : 4);
    leafletMap.current = map;

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
    }).addTo(map);

    const markers = L.markerClusterGroup();
    clusterLayer.current = markers;

    const geo = properties.filter((p) => p.latitude && p.longitude);
    geo.forEach((p) => {
      const score = p.opportunity_score ?? 0;
      const color = score >= 70 ? "#22c55e" : score >= 40 ? "#eab308" : "#ef4444";
      const icon = L.divIcon({
        className: "",
        html: `<div style="background:${color};width:10px;height:10px;border-radius:50%;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,.4)"></div>`,
      });
      L.marker([p.latitude!, p.longitude!], { icon })
        .bindTooltip(`<b>${p.city}/${p.state}</b><br>R$ ${p.current_value?.toLocaleString("pt-BR")}`)
        .on("click", () => setSelected(p))
        .addTo(markers);
    });

    map.addLayer(markers);

    return () => {
      map.remove();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [properties, center]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapRef} className="w-full h-full z-0" />

      {selected && (
        <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg p-4 z-[1000] max-w-xs">
          <button
            className="absolute top-2 right-2 text-gray-400 hover:text-gray-700 text-lg"
            onClick={() => setSelected(null)}
          >
            ×
          </button>
          <p className="font-semibold text-gray-800 text-sm mb-1">{selected.property_type}</p>
          <p className="text-gray-600 text-xs mb-1">{selected.city}/{selected.state}</p>
          <p className="text-blue-700 font-bold">R$ {selected.current_value?.toLocaleString("pt-BR")}</p>
          {selected.discount_percent && (
            <p className="text-green-600 text-xs">{selected.discount_percent.toFixed(1)}% de desconto</p>
          )}
          {selected.opportunity_score !== null && (
            <p className="text-xs text-gray-500 mt-1">Score: {selected.opportunity_score}</p>
          )}
          <a
            href={`/imoveis/${selected.id}`}
            className="mt-2 block text-center bg-blue-600 text-white text-xs rounded py-1.5 hover:bg-blue-700 transition"
          >
            Ver detalhes
          </a>
        </div>
      )}

      <div className="absolute top-4 right-4 bg-white rounded shadow px-3 py-2 text-xs text-gray-600 z-[1000]">
        <div className="flex items-center gap-1.5 mb-1"><span className="w-3 h-3 rounded-full bg-green-500 inline-block" /> Score ≥ 70</div>
        <div className="flex items-center gap-1.5 mb-1"><span className="w-3 h-3 rounded-full bg-yellow-400 inline-block" /> Score 40–69</div>
        <div className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-red-500 inline-block" /> Score &lt; 40</div>
      </div>
    </div>
  );
}
