import type { ChatResponse } from "./types";

export async function sendMessage(
  session_id: string,
  message: string
): Promise<ChatResponse> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id, message }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || "Request failed");
  }
  return res.json();
}

export async function clearSession(session_id: string): Promise<void> {
  await fetch(`/api/session/${session_id}`, { method: "DELETE" });
}
