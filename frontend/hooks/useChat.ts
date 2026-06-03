"use client";
import { useState, useCallback } from "react";
import { sendMessage, clearSession } from "@/lib/api";
import { useSession } from "./useSession";
import type { UIMessage } from "@/lib/types";

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

      try {
        const res = await sendMessage(sessionId, text);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: res.message,
            restaurants: res.restaurants,
            needs_followup: res.needs_followup,
          },
        ]);
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "Something went wrong";
        setError(msg);
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
