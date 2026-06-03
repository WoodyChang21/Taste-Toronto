"use client";
import RestaurantListItem from "./RestaurantCard";
import type { UIMessage } from "@/lib/types";

export default function MessageBubble({
  message,
  hoveredId,
  onHover,
  showMapButton,
  showMap,
  onToggleMap,
}: {
  message: UIMessage;
  hoveredId?: string | null;
  onHover?: (id: string | null) => void;
  showMapButton?: boolean;
  showMap?: boolean;
  onToggleMap?: () => void;
}) {
  const isUser = message.role === "user";
  const hasRestaurants = message.restaurants && message.restaurants.length > 0;

  if (isUser) {
    return (
      <div className="msg-enter" style={{ display: "flex", justifyContent: "flex-end", marginBottom: "1.25rem" }}>
        <div
          style={{
            background: "var(--pill-bg)",
            color: "var(--pill-text)",
            borderRadius: "999px",
            padding: "0.6rem 1.25rem",
            fontSize: "0.9rem",
            fontWeight: 300,
            maxWidth: "70%",
            lineHeight: 1.5,
          }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="msg-enter" style={{ marginBottom: "1.75rem" }}>
      {/* AI prose intro */}
      {message.content && (
        <p
          style={{
            fontSize: "0.9rem",
            color: "var(--ink-light)",
            lineHeight: 1.75,
            fontWeight: 300,
            maxWidth: "640px",
            marginBottom: hasRestaurants ? "1rem" : 0,
          }}
        >
          {message.content}
        </p>
      )}

      {/* Map toggle button — only on the latest message with restaurants */}
      {hasRestaurants && showMapButton && (
        <div style={{ marginBottom: "1.25rem" }}>
          <button
            onClick={onToggleMap}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.35rem",
              background: showMap ? "var(--ink)" : "transparent",
              color: showMap ? "var(--cream)" : "var(--ink-muted)",
              border: `1px solid ${showMap ? "var(--ink)" : "var(--border)"}`,
              borderRadius: "999px",
              padding: "0.3rem 0.85rem",
              fontSize: "0.76rem",
              fontFamily: "var(--font-dm-sans), sans-serif",
              fontWeight: 400,
              cursor: "pointer",
              transition: "all 0.15s ease",
              letterSpacing: "0.02em",
            }}
            onMouseEnter={(e) => {
              if (!showMap) {
                e.currentTarget.style.background = "var(--cream-dark)";
                e.currentTarget.style.borderColor = "var(--ink-muted)";
                e.currentTarget.style.color = "var(--ink)";
              }
            }}
            onMouseLeave={(e) => {
              if (!showMap) {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.borderColor = "var(--border)";
                e.currentTarget.style.color = "var(--ink-muted)";
              }
            }}
          >
            <span style={{ fontSize: "0.78rem" }}>⊕</span>
            {showMap ? "Hide map" : "View on map"}
          </button>
        </div>
      )}

      {/* Editorial restaurant list */}
      {hasRestaurants && (
        <div style={{ maxWidth: "680px" }}>
          {message.restaurants!.map((r, i) => (
            <RestaurantListItem
              key={r.id}
              r={r}
              index={i + 1}
              isLast={i === message.restaurants!.length - 1}
              highlighted={hoveredId === null ? undefined : hoveredId === r.id}
              onHover={onHover}
            />
          ))}
        </div>
      )}
    </div>
  );
}
