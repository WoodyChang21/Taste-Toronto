const CHIP_SETS: Record<string, string[]> = {
  group_size: ["Just me", "Just us two", "Small group (3–4)", "Party of 5–6", "Large group (7+)"],
  budget: ["Casual (under $30)", "Mid-range ($30–60)", "Nice out ($60–100)", "Splurge"],
};

function detectChipSet(message: string): string[] {
  const lower = message.toLowerCase();
  if (lower.includes("how many") || lower.includes("group") || lower.includes("people") || lower.includes("party")) return CHIP_SETS.group_size;
  if (lower.includes("budget") || lower.includes("spend") || lower.includes("price") || lower.includes("range")) return CHIP_SETS.budget;
  return [];
}

export default function FollowUpChips({ question, onSelect }: { question: string; onSelect: (chip: string) => void }) {
  const chips = detectChipSet(question);
  if (!chips.length) return null;

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "0.75rem" }}>
      {chips.map((chip) => (
        <button
          key={chip}
          onClick={() => onSelect(chip)}
          style={{
            background: "transparent",
            border: "1px solid var(--border)",
            borderRadius: "999px",
            padding: "0.3rem 0.85rem",
            fontSize: "0.78rem",
            color: "var(--ink-light)",
            cursor: "pointer",
            transition: "all 0.15s ease",
            fontFamily: "var(--font-dm-sans), sans-serif",
            fontWeight: 300,
          }}
          onMouseEnter={(e) => {
            (e.target as HTMLButtonElement).style.background = "var(--pill-bg)";
            (e.target as HTMLButtonElement).style.color = "var(--pill-text)";
            (e.target as HTMLButtonElement).style.borderColor = "var(--pill-bg)";
          }}
          onMouseLeave={(e) => {
            (e.target as HTMLButtonElement).style.background = "transparent";
            (e.target as HTMLButtonElement).style.color = "var(--ink-light)";
            (e.target as HTMLButtonElement).style.borderColor = "var(--border)";
          }}
        >
          {chip}
        </button>
      ))}
    </div>
  );
}
