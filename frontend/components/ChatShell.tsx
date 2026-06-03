"use client";
import { useState, useMemo } from "react";
import { useChat } from "@/hooks/useChat";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import LocationSearch from "./LocationSearch";
import MapPanel from "./MapPanel";
import type { ScoredRestaurant } from "@/lib/types";

export default function ChatShell() {
  const { messages, loading, error, send, reset } = useChat();
  const isEmpty = messages.length === 0;
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [showMap, setShowMap] = useState(false);

  // Latest message that has restaurants — drives the map panel
  const mapRestaurants = useMemo<ScoredRestaurant[]>(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const r = messages[i].restaurants;
      if (r && r.length > 0) return r;
    }
    return [];
  }, [messages]);

  const hasRestaurants = mapRestaurants.length > 0;

  const handleLocationSelect = (location: string) => {
    if (location) send(`I'm looking for restaurants near ${location}.`);
  };

  return (
    <div style={{ display: "flex", height: "100dvh", overflow: "hidden", background: "var(--cream)" }}>

      {/* ── Left: chat column ── */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          flex: showMap && hasRestaurants ? "0 0 58%" : "1",
          minWidth: 0,
          transition: "flex 0.3s ease",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <header
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "1rem 1.5rem",
            borderBottom: "1px solid var(--border)",
            background: "var(--cream)",
            position: "relative",
            zIndex: 10,
            flexShrink: 0,
          }}
        >
          <h1
            style={{
              fontFamily: "var(--font-cormorant), Georgia, serif",
              fontWeight: 300,
              fontSize: "1.2rem",
              letterSpacing: "0.06em",
              color: "var(--ink)",
              margin: 0,
              position: "absolute",
              left: "50%",
              transform: "translateX(-50%)",
            }}
          >
            Taste Toronto
          </h1>

          <div style={{ width: "80px" }} />

          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <LocationSearch onSelect={handleLocationSelect} />
            {!isEmpty && (
              <button
                onClick={reset}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                  color: "var(--ink-muted)",
                  fontFamily: "var(--font-dm-sans), sans-serif",
                  fontWeight: 300,
                  padding: "0.25rem 0.5rem",
                  transition: "color 0.15s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "var(--ink)")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "var(--ink-muted)")}
              >
                Start over
              </button>
            )}
          </div>
        </header>

        {/* Body */}
        {isEmpty ? (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", opacity: 0.45 }}>
            <p
              style={{
                fontFamily: "var(--font-cormorant), Georgia, serif",
                fontSize: "1rem",
                fontWeight: 300,
                color: "var(--ink-muted)",
                letterSpacing: "0.04em",
                margin: 0,
              }}
            >
              Where should I eat tonight?
            </p>
          </div>
        ) : (
          <MessageList
            messages={messages}
            loading={loading}
            onChipSelect={send}
            hoveredId={hoveredId}
            onHover={setHoveredId}
            showMap={showMap}
            onToggleMap={() => setShowMap((v) => !v)}
            hasRestaurants={hasRestaurants}
          />
        )}

        {/* Error */}
        {error && (
          <div style={{ textAlign: "center", fontSize: "0.78rem", color: "#c0392b", padding: "0.4rem 1rem", flexShrink: 0 }}>
            {error}
          </div>
        )}

        {/* Input */}
        <div style={{ padding: "0.75rem 1.5rem 0.5rem", background: "var(--cream)", flexShrink: 0 }}>
          <div style={{ maxWidth: "680px", margin: "0 auto" }}>
            <ChatInput onSend={send} disabled={loading} />
            <p
              style={{
                textAlign: "center",
                fontSize: "0.7rem",
                color: "var(--ink-faint)",
                margin: "0.4rem 0 0",
                fontWeight: 300,
              }}
            >
              AI suggestions for reference only · Always verify with the restaurant directly
            </p>
          </div>
        </div>
      </div>

      {/* ── Right: map panel (only when user opens it) ── */}
      {showMap && hasRestaurants && (
        <div
          style={{
            flex: "0 0 42%",
            borderLeft: "1px solid var(--border)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* Close button */}
          <button
            onClick={() => setShowMap(false)}
            title="Close map"
            style={{
              position: "absolute",
              top: "0.75rem",
              left: "0.75rem",
              zIndex: 20,
              width: 30,
              height: 30,
              borderRadius: "50%",
              background: "var(--cream)",
              border: "1px solid var(--border)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "1rem",
              color: "var(--ink)",
              boxShadow: "0 1px 4px rgba(0,0,0,0.15)",
              transition: "background 0.15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--cream-dark)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "var(--cream)")}
          >
            ×
          </button>
          <MapPanel
            restaurants={mapRestaurants}
            hoveredId={hoveredId}
            onMarkerHover={setHoveredId}
          />
        </div>
      )}

    </div>
  );
}
