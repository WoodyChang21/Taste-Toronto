export default function TypingIndicator() {
  return (
    <div
      className="msg-enter"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.6rem",
        padding: "0.25rem 0",
        marginBottom: "1.25rem",
      }}
    >
      <span
        style={{
          fontSize: "0.82rem",
          color: "var(--ink-muted)",
          fontWeight: 300,
          fontStyle: "italic",
          letterSpacing: "0.01em",
        }}
      >
        Taste Toronto is thinking
      </span>
      <span className="dot-pulse" style={{ display: "inline-flex", alignItems: "center", gap: "2px" }}>
        <span />
        <span />
        <span />
      </span>
    </div>
  );
}
