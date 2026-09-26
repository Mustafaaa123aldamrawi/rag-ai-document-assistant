import { supabase } from "./supabase";

const API_URL =
  process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";

export async function api<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const session = supabase
    ? (await supabase.auth.getSession()).data.session
    : null;

  const headers = new Headers(init?.headers || {});
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });

  const payload =
    response.status === 204 ? null : await response.json();

  if (!response.ok) {
    const detail =
      typeof payload?.detail === "string"
        ? payload.detail
        : payload?.detail?.message || "Request failed.";
    throw new Error(detail);
  }

  return payload as T;
}
