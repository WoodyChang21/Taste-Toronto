"use client";
import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import FollowUpChips from "./FollowUpChips";
import TypingIndicator from "./TypingIndicator";
import type { UIMessage } from "@/lib/types";

export default function MessageList({
  messages,
  loading,
  onChipSelect,
  hoveredId,
  onHover,
  showMap,
  onToggleMap,
  hasRestaurants,
}: {
  messages: UIMessage[];
  loading: boolean;
  onChipSelect: (text: string) => void;
  hoveredId?: string | null;
  onHover?: (id: string | null) => void;
  showMap?: boolean;
  onToggleMap?: () => void;
  hasRestaurants?: boolean;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const lastAssistant = messages.findLast((m) => m.role === "assistant");

  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        padding: "2rem 1.5rem 1rem",
        maxWidth: "760px",
        width: "100%",
        margin: "0 auto",
      }}
    >
      {messages.map((msg, i) => {
        const isLastWithRestaurants =
          msg.restaurants && msg.restaurants.length > 0 &&
          i === messages.findLastIndex((m) => m.restaurants && m.restaurants.length > 0);
        return (
          <MessageBubble
            key={i}
            message={msg}
            hoveredId={hoveredId}
            onHover={onHover}
            showMapButton={isLastWithRestaurants}
            showMap={showMap}
            onToggleMap={onToggleMap}
          />
        );
      })}

      {loading && <TypingIndicator />}

      {!loading && lastAssistant?.needs_followup && lastAssistant.content && (
        <FollowUpChips question={lastAssistant.content} onSelect={onChipSelect} />
      )}

      <div ref={bottomRef} style={{ height: "1px" }} />
    </div>
  );
}
