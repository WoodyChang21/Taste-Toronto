// Empty state — no longer used; welcome state is handled in ChatShell
export default function OccasionSelector({ onSelect }: { onSelect: (p: string) => void }) {
  void onSelect;
  return null;
}
