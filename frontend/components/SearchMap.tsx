"use client";

import { useEffect, useRef, useState } from "react";
import { setOptions, importLibrary } from "@googlemaps/js-api-loader";
import { MarkerClusterer } from "@googlemaps/markerclusterer";
import type { Property } from "@/lib/types";

setOptions({
  key: process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY ?? "",
  v: "weekly",
});

function scoreColor(score: number): string {
  if (score >= 70) return "#22c55e";
  if (score >= 40) return "#eab308";
  return "#ef4444";
}

interface Props {
  properties: Property[];
  center: [number, number] | null;
  onCenterChange: (c: [number, number]) => void;
  radiusKm: number;
}

export default function SearchMap({ properties, center }: Props) {
  const divRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const clustererRef = useRef<MarkerClusterer | null>(null);
  const [selected, setSelected] = useState<Property | null>(null);

  useEffect(() => {
    if (!divRef.current) return;
    let cancelled = false;

    const init = async () => {
      const { Map } = await importLibrary("maps");
      const { AdvancedMarkerElement } = await importLibrary("marker");

      if (cancelled || !divRef.current) return;

      if (!mapRef.current) {
        mapRef.current = new Map(divRef.current, {
          center: center ? { lat: center[0], lng: center[1] } : { lat: -15, lng: -50 },
          zoom: center ? 11 : 4,
          mapId: "search_map",
          mapTypeControl: false,
          streetViewControl: false,
        });
      } else if (center) {
        mapRef.current.setCenter({ lat: center[0], lng: center[1] });
        mapRef.current.setZoom(11);
      }

      const map = mapRef.current;

      if (clustererRef.current) {
        clustererRef.current.clearMarkers();
        clustererRef.current = null;
      }

      const geo = properties.filter((p) => p.latitude && p.longitude);
      const infoWindow = new google.maps.InfoWindow();

      const newMarkers = geo.map((p) => {
        const score = p.opportunity_score ?? 0;
        const pin = document.createElement("div");
        pin.style.cssText = [
          "width:14px;height:14px;border-radius:50%",
          `background:${scoreColor(score)}`,
          "border:2px solid white",
          "box-shadow:0 1px 4px rgba(0,0,0,.4)",
          "cursor:pointer",
        ].join(";");

        const marker = new AdvancedMarkerElement({
          map,
          position: { lat: p.latitude!, lng: p.longitude! },
          content: pin,
          title: `${p.city}/${p.state}`,
        });

        marker.addListener("click", () => {
          infoWindow.setContent(
            `<div style="font-size:13px">
               <strong>${p.property_type ?? "Imóvel"}</strong><br/>
               ${p.city}/${p.state}<br/>
               <span style="color:#1d4ed8;font-weight:bold">R$ ${p.current_value?.toLocaleString("pt-BR")}</span>
               ${p.discount_percent ? `<br/><span style="color:#16a34a">${p.discount_percent.toFixed(1)}% de desconto</span>` : ""}
               <br/><a href="/imoveis/${p.id}" style="color:#3b82f6;text-decoration:underline;font-size:11px">Ver detalhes →</a>
             </div>`
          );
          infoWindow.open(map, marker as unknown as google.maps.MVCObject);
          setSelected(p);
        });

        return marker;
      });

      clustererRef.current = new MarkerClusterer({
        map,
        markers: newMarkers as unknown as google.maps.Marker[],
      });
    };

    init();
    return () => { cancelled = true; };
  }, [properties, center]);

  return (
    <div className="relative w-full h-full">
      <div ref={divRef} className="w-full h-full" />

      {selected && (
        <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg p-4 z-10 max-w-xs">
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
          {selected.opportunity_score != null && (
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

      <div className="absolute top-4 right-4 bg-white rounded shadow px-3 py-2 text-xs text-gray-600 z-10">
        <div className="flex items-center gap-1.5 mb-1">
          <span className="w-3 h-3 rounded-full bg-green-500 inline-block" /> Score ≥ 70
        </div>
        <div className="flex items-center gap-1.5 mb-1">
          <span className="w-3 h-3 rounded-full bg-yellow-400 inline-block" /> Score 40–69
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-red-500 inline-block" /> Score &lt; 40
        </div>
      </div>
    </div>
  );
}
