"use client";
import { useEffect, useState } from "react";
import { APIProvider, Map, AdvancedMarker } from "@vis.gl/react-google-maps";
import type { ScoredRestaurant } from "@/lib/types";

const TORONTO = { lat: 43.6532, lng: -79.3832 };

function computeCenter(restaurants: ScoredRestaurant[]) {
  const valid = restaurants.filter((r) => r.latitude && r.longitude);
  if (!valid.length) return TORONTO;
  const lat = valid.reduce((s, r) => s + r.latitude!, 0) / valid.length;
  const lng = valid.reduce((s, r) => s + r.longitude!, 0) / valid.length;
  return { lat, lng };
}

export default function MapPanel({
  restaurants,
  hoveredId,
  onMarkerHover,
}: {
  restaurants: ScoredRestaurant[];
  hoveredId: string | null;
  onMarkerHover: (id: string | null) => void;
}) {
  const [apiKey, setApiKey] = useState<string>("");

  useEffect(() => {
    setApiKey(process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY || "");
  }, []);

  const center = computeCenter(restaurants);

  if (!apiKey) return null;

  return (
    <APIProvider apiKey={apiKey}>
      <Map
        defaultCenter={center}
        defaultZoom={13}
        disableDefaultUI
        style={{ width: "100%", height: "100%" }}
        mapId="taste-toronto-map"
      >
        {restaurants.map((r) => {
          if (!r.latitude || !r.longitude) return null;
          const isActive = hoveredId === r.id;
          return (
            <AdvancedMarker
              key={r.id}
              position={{ lat: r.latitude, lng: r.longitude }}
              onMouseEnter={() => onMarkerHover(r.id)}
              onMouseLeave={() => onMarkerHover(null)}
              onClick={() => {
                const el = document.getElementById(`restaurant-${r.id}`);
                el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
              }}
              zIndex={isActive ? 10 : 1}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.25rem",
                  background: isActive ? "#1A1A1A" : "#EFEFEB",
                  color: isActive ? "#EFEFEB" : "#1A1A1A",
                  border: `1.5px solid ${isActive ? "#1A1A1A" : "#999"}`,
                  borderRadius: "999px",
                  padding: isActive ? "0.3rem 0.6rem" : "0.22rem 0.5rem",
                  fontSize: isActive ? "0.82rem" : "0.75rem",
                  fontWeight: 600,
                  fontFamily: "Georgia, serif",
                  boxShadow: isActive ? "0 3px 10px rgba(0,0,0,0.35)" : "0 1px 5px rgba(0,0,0,0.18)",
                  transition: "all 0.15s ease",
                  cursor: "pointer",
                  userSelect: "none",
                  whiteSpace: "nowrap",
                  transform: isActive ? "scale(1.1)" : "scale(1)",
                  transformOrigin: "bottom center",
                }}
              >
                <span style={{ color: isActive ? "#F5C842" : "#C9A84C", fontSize: "0.72rem", lineHeight: 1 }}>★</span>
                {r.rating.toFixed(1)}
              </div>
            </AdvancedMarker>
          );
        })}
      </Map>
    </APIProvider>
  );
}
