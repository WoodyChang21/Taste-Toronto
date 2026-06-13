"use client";
import { useState, useCallback } from "react";
import { clearSession } from "@/lib/api";
import { useSession } from "./useSession";
import type { UIMessage, ScoredRestaurant } from "@/lib/types";

const API_BASE = "/api";

export function useChat() {
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { sessionId, resetSession } = useSession();

  const send = useCallback(
    async (text: string) => {
      if (!sessionId || !text.trim()) return;

      setMessages((prev) => [...prev, { role: "user", content: text }]);
      setLoading(true);
      setError(null);

      // Append a blank assistant message that we stream into
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "", restaurants: [], needs_followup: false },
      ]);

      try {
        const res = await fetch(`${API_BASE}/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, message: text }),
        });

        if (!res.ok || !res.body) {
          throw new Error(`Request failed: ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const raw = line.slice(6).trim();
            if (raw === "[DONE]") break;

            let event: { type: string; content?: string; restaurants?: ScoredRestaurant[]; question?: string; message?: string };
            try {
              event = JSON.parse(raw);
            } catch {
              continue;
            }

            if (event.type === "text" && event.content) {
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last?.role === "assistant") {
                  next[next.length - 1] = { ...last, content: last.content + event.content };
                }
                return next;
              });
            } else if (event.type === "restaurants" && event.restaurants) {
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last?.role === "assistant") {
                  next[next.length - 1] = { ...last, restaurants: event.restaurants };
                }
                return next;
              });
            } else if (event.type === "followup" && event.question) {
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last?.role === "assistant") {
                  next[next.length - 1] = {
                    ...last,
                    content: event.question ?? "",
                    needs_followup: true,
                  };
                }
                return next;
              });
            } else if (event.type === "error") {
              setError(event.message ?? "Something went wrong");
            }
          }
        }
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "Something went wrong";
        setError(msg);
        // Remove the blank assistant message on error
        setMessages((prev) => {
          const next = [...prev];
          if (next[next.length - 1]?.role === "assistant" && !next[next.length - 1].content) {
            next.pop();
          }
          return next;
        });
      } finally {
        setLoading(false);
      }
    },
    [sessionId]
  );

  const reset = useCallback(async () => {
    if (sessionId) await clearSession(sessionId);
    resetSession();
    setMessages([]);
    setError(null);
  }, [sessionId, resetSession]);

  return { messages, loading, error, send, reset, sessionId };
}
