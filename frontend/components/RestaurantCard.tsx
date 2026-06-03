import type { ScoredRestaurant } from "@/lib/types";

export default function RestaurantListItem({
  r,
  index,
  isLast,
  highlighted,
  onHover,
}: {
  r: ScoredRestaurant;
  index: number;
  isLast: boolean;
  highlighted?: boolean;
  onHover?: (id: string | null) => void;
}) {
  const reserveHref = r.reservation_url || r.website;

  return (
    <div
      id={`restaurant-${r.id}`}
      onMouseEnter={() => onHover?.(r.id)}
      onMouseLeave={() => onHover?.(null)}
      style={{
        paddingBottom: "1.5rem",
        marginBottom: isLast ? 0 : "1.5rem",
        transition: "opacity 0.2s",
        opacity: highlighted === false ? 0.45 : 1,
      }}
    >
      {/* Name */}
      <h3
        style={{
          fontFamily: "var(--font-cormorant), Georgia, serif",
          fontSize: "1.2rem",
          fontWeight: 500,
          color: "var(--ink)",
          marginBottom: "0.35rem",
          lineHeight: 1.3,
        }}
      >
        {index}. {r.name}
      </h3>

      {/* Metadata line */}
      <p
        style={{
          fontSize: "0.78rem",
          color: "var(--ink-muted)",
          marginBottom: "0.75rem",
          letterSpacing: "0.01em",
        }}
      >
        ★ {r.rating.toFixed(1)}
        <span style={{ margin: "0 0.4rem" }}>({r.review_count.toLocaleString()})</span>
        <span style={{ margin: "0 0.4rem", color: "var(--ink-faint)" }}>·</span>
        {r.price_range}
        <span style={{ margin: "0 0.4rem", color: "var(--ink-faint)" }}>·</span>
        {r.neighborhood}
        {r.cuisine && (
          <>
            <span style={{ margin: "0 0.4rem", color: "var(--ink-faint)" }}>·</span>
            {r.cuisine}
          </>
        )}
      </p>

      {/* Photo + description row */}
      <div style={{ display: "flex", gap: "1rem", alignItems: "flex-start" }}>
        {/* Photo */}
        <div
          style={{
            flexShrink: 0,
            width: 110,
            height: 82,
            borderRadius: 6,
            overflow: "hidden",
            background: "var(--cream-dark)",
          }}
        >
          <img
            src={`/api/photo/${r.id}`}
            alt={r.name}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
            onError={(e) => {
              e.currentTarget.parentElement!.style.display = "none";
            }}
          />
        </div>

        {/* Description + reserve */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {r.description && (
            <p
              style={{
                fontSize: "0.88rem",
                color: "var(--ink-light)",
                lineHeight: 1.65,
                marginBottom: "0.5rem",
                fontWeight: 300,
              }}
            >
              {r.description}
            </p>
          )}

          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
            {reserveHref && (
              <a
                href={reserveHref}
                target="_blank"
                rel="noopener noreferrer"
                style={{ fontSize: "0.75rem", color: "var(--ink-muted)", textDecoration: "underline", textUnderlineOffset: "3px" }}
              >
                {r.reservation_url ? "Reserve a table →" : "Visit website →"}
              </a>
            )}
            {r.google_maps_url && (
              <a
                href={r.google_maps_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ fontSize: "0.75rem", color: "var(--ink-muted)", textDecoration: "underline", textUnderlineOffset: "3px" }}
              >
                View on Google Maps →
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Divider */}
      {!isLast && (
        <hr
          style={{
            border: "none",
            borderTop: "1px solid var(--border)",
            marginTop: "1.5rem",
          }}
        />
      )}
    </div>
  );
}
