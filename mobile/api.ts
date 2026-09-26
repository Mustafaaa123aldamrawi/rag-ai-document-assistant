const API_URL =
  process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";

let accessToken: string | null = null;

export function setApiAccessToken(token: string | null) {
  accessToken = token;
}

export function getApiBaseUrl() {
  return API_URL;
}

export async function api<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const headers = new Headers(init?.headers || {});
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload =
    response.status === 204
      ? null
      : contentType.includes("application/json")
      ? await response.json()
      : await response.text();

  if (!response.ok) {
    const detail =
      typeof payload === "string"
        ? payload
        : typeof payload?.detail === "string"
        ? payload.detail
        : payload?.detail?.message || "Request failed.";
    throw new Error(detail);
  }

  return payload as T;
}
