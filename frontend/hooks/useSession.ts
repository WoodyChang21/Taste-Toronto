"use client";
import { useState, useEffect } from "react";

export function useSession() {
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    const stored = localStorage.getItem("taste_toronto_session_id");
    if (stored) {
      setSessionId(stored);
    } else {
      const id = crypto.randomUUID();
      localStorage.setItem("taste_toronto_session_id", id);
      setSessionId(id);
    }
  }, []);

  const resetSession = () => {
    const id = crypto.randomUUID();
    localStorage.setItem("taste_toronto_session_id", id);
    setSessionId(id);
  };

  return { sessionId, resetSession };
}
