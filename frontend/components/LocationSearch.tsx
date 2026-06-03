"use client";
import { useState, useEffect, useRef, useCallback } from "react";

interface Suggestion {
  type: "place" | "query";
  place_id: string | null;
  text: string;
  main_text: string;
  secondary_text: string;
}

export default function LocationSearch({ onSelect }: { onSelect: (location: string) => void }) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const sessionToken = useRef(crypto.randomUUID());
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchSuggestions = useCallback(async (value: string) => {
    if (value.length < 2) { setSuggestions([]); return; }
    setLoading(true);
    try {
      const res = await fetch("/api/autocomplete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input: value, session_token: sessionToken.current }),
      });
      const data = await res.json();
      setSuggestions(data.suggestions || []);
    } catch { setSuggestions([]); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(input), 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [input, fetchSuggestions]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSelect = (s: Suggestion) => {
    const location = s.main_text || s.text;
    setInput(location);
    setOpen(false);
    setSuggestions([]);
    sessionToken.current = crypto.randomUUID();
    onSelect(location);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: "0.78rem",
          color: "var(--ink-muted)",
          display: "flex",
          alignItems: "center",
          gap: "0.3rem",
          padding: "0.25rem 0.5rem",
          borderRadius: "4px",
          transition: "color 0.15s",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.color = "var(--ink)")}
        onMouseLeave={(e) => (e.currentTarget.style.color = "var(--ink-muted)")}
      >
        <svg width="10" height="13" viewBox="0 0 10 13" fill="none">
          <path d="M5 0C2.24 0 0 2.24 0 5c0 3.75 5 8 5 8s5-4.25 5-8c0-2.76-2.24-5-5-5zm0 6.5A1.5 1.5 0 1 1 5 3.5a1.5 1.5 0 0 1 0 3z" fill="currentColor"/>
        </svg>
        {input || "Set area"}
      </button>
    );
  }

  return (
    <div ref={containerRef} style={{ position: "relative" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.4rem",
          background: "white",
          border: "1px solid var(--border)",
          borderRadius: "999px",
          padding: "0.3rem 0.75rem",
        }}
      >
        <input
          autoFocus
          type="text"
          value={input}
          onChange={(e) => { setInput(e.target.value); }}
          placeholder="Search neighbourhood…"
          style={{
            border: "none",
            outline: "none",
            fontSize: "0.8rem",
            fontFamily: "var(--font-dm-sans), sans-serif",
            fontWeight: 300,
            color: "var(--ink)",
            background: "transparent",
            width: "150px",
          }}
        />
        {loading && <span style={{ fontSize: "0.7rem", color: "var(--ink-muted)" }}>…</span>}
        {input && (
          <button
            onClick={() => { setInput(""); setSuggestions([]); onSelect(""); setOpen(false); }}
            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--ink-muted)", fontSize: "0.8rem", lineHeight: 1 }}
          >×</button>
        )}
      </div>

      {suggestions.length > 0 && (
        <ul
          style={{
            position: "absolute",
            top: "calc(100% + 6px)",
            left: 0,
            right: 0,
            background: "white",
            border: "1px solid var(--border)",
            borderRadius: "12px",
            overflow: "hidden",
            boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
            zIndex: 50,
            listStyle: "none",
            margin: 0,
            padding: "0.25rem 0",
          }}
        >
          {suggestions.map((s, i) => (
            <li key={i}>
              <button
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => handleSelect(s)}
                style={{
                  width: "100%",
                  textAlign: "left",
                  padding: "0.5rem 0.85rem",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "0.8rem",
                  fontFamily: "var(--font-dm-sans), sans-serif",
                  color: "var(--ink)",
                }}
              >
                {s.main_text}
                {s.secondary_text && (
                  <span style={{ color: "var(--ink-muted)", marginLeft: "0.4rem" }}>{s.secondary_text}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
