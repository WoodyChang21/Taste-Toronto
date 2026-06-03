"use client";
import { useState, useRef, useEffect } from "react";

const PLACEHOLDERS = [
  "Best ramen in Kensington Market…",
  "Quiet spot for a work lunch near King West…",
  "Hidden gem with a great patio…",
  "Late night spot after a show downtown…",
  "Omakase experience, budget $150/person…",
  "Somewhere lively for a group of 8…",
  "Best dim sum in Scarborough…",
  "Cozy date night, not too loud…",
];

export default function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled?: boolean;
}) {
  const [value, setValue] = useState("");
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Cycle placeholder every 3.5s when input is empty and not focused
  const [focused, setFocused] = useState(false);
  useEffect(() => {
    if (focused || value) return;
    const id = setInterval(() => setPlaceholderIdx((i) => (i + 1) % PLACEHOLDERS.length), 3500);
    return () => clearInterval(id);
  }, [focused, value]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [value]);

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-end",
        gap: "0.5rem",
        background: "white",
        border: "1px solid var(--border)",
        borderRadius: "999px",
        padding: "0.65rem 0.65rem 0.65rem 1.4rem",
        boxShadow: "0 1px 8px rgba(0,0,0,0.04)",
        transition: "box-shadow 0.2s ease",
      }}
      onFocus={() => {}}
    >
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKey}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={PLACEHOLDERS[placeholderIdx]}
        disabled={disabled}
        style={{
          flex: 1,
          resize: "none",
          background: "transparent",
          border: "none",
          outline: "none",
          fontSize: "0.9rem",
          color: "var(--ink)",
          fontFamily: "var(--font-dm-sans), sans-serif",
          fontWeight: 300,
          lineHeight: 1.5,
          maxHeight: "120px",
          overflow: "auto",
        }}
      />
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        style={{
          width: "2.2rem",
          height: "2.2rem",
          borderRadius: "50%",
          background: value.trim() && !disabled ? "var(--pill-bg)" : "var(--cream-dark)",
          border: "none",
          cursor: value.trim() && !disabled ? "pointer" : "default",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transition: "background 0.2s ease",
          flexShrink: 0,
        }}
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path
            d="M7 12V2M2 7l5-5 5 5"
            stroke={value.trim() && !disabled ? "white" : "var(--ink-faint)"}
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </div>
  );
}
