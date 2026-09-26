import * as SecureStore from "expo-secure-store";

export type AuthSession = {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  token_type?: string;
  user?: {
    id?: string;
    email?: string;
  };
};

export type AuthResult = {
  session: AuthSession | null;
  message?: string;
};

const SUPABASE_URL =
  process.env.EXPO_PUBLIC_SUPABASE_URL?.replace(/\/$/, "") || "";
const SUPABASE_ANON_KEY =
  process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY || "";

const SESSION_KEY = "avia.auth.session";

export const authConfigured = Boolean(
  SUPABASE_URL && SUPABASE_ANON_KEY
);

function authHeaders(extra?: Record<string, string>) {
  return {
    apikey: SUPABASE_ANON_KEY,
    "Content-Type": "application/json",
    ...(extra || {}),
  };
}

function normalizeSession(payload: any): AuthSession | null {
  const accessToken = String(payload?.access_token || "").trim();
  const refreshToken = String(payload?.refresh_token || "").trim();
  if (!accessToken || !refreshToken) return null;

  const now = Math.floor(Date.now() / 1000);
  const expiresIn = Number(payload?.expires_in || 3600);
  const expiresAt = Number(payload?.expires_at || now + expiresIn);

  return {
    access_token: accessToken,
    refresh_token: refreshToken,
    expires_at: expiresAt,
    token_type: payload?.token_type,
    user: payload?.user
      ? {
          id: payload.user.id,
          email: payload.user.email,
        }
      : undefined,
  };
}

async function persistSession(session: AuthSession | null) {
  if (!session) {
    await SecureStore.deleteItemAsync(SESSION_KEY);
    return;
  }
  await SecureStore.setItemAsync(
    SESSION_KEY,
    JSON.stringify(session)
  );
}

async function authRequest(
  path: string,
  body: Record<string, unknown>,
  accessToken?: string
) {
  if (!authConfigured) {
    throw new Error("Authentication is not configured.");
  }

  const response = await fetch(`${SUPABASE_URL}${path}`, {
    method: "POST",
    headers: authHeaders(
      accessToken
        ? { Authorization: `Bearer ${accessToken}` }
        : undefined
    ),
    body: JSON.stringify(body),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message =
      payload?.msg ||
      payload?.message ||
      payload?.error_description ||
      payload?.error ||
      "Authentication request failed.";
    throw new Error(String(message));
  }
  return payload;
}

export async function signIn(
  email: string,
  password: string
): Promise<AuthResult> {
  const payload = await authRequest(
    "/auth/v1/token?grant_type=password",
    { email, password }
  );
  const session = normalizeSession(payload);
  if (!session) {
    throw new Error("Login succeeded without a usable session.");
  }
  await persistSession(session);
  return { session };
}

export async function signUp(
  email: string,
  password: string
): Promise<AuthResult> {
  const payload = await authRequest("/auth/v1/signup", {
    email,
    password,
  });
  const session = normalizeSession(payload);
  if (session) {
    await persistSession(session);
    return { session };
  }

  return {
    session: null,
    message:
      "Account created. Check your email to confirm the account, then sign in.",
  };
}

export async function refreshSession(
  refreshToken: string
): Promise<AuthSession> {
  const payload = await authRequest(
    "/auth/v1/token?grant_type=refresh_token",
    { refresh_token: refreshToken }
  );
  const session = normalizeSession(payload);
  if (!session) {
    throw new Error("Unable to refresh the login session.");
  }
  await persistSession(session);
  return session;
}

export async function restoreSession(): Promise<AuthSession | null> {
  if (!authConfigured) return null;

  const raw = await SecureStore.getItemAsync(SESSION_KEY);
  if (!raw) return null;

  try {
    const session = JSON.parse(raw) as AuthSession;
    const now = Math.floor(Date.now() / 1000);
    if (
      session?.access_token &&
      session?.expires_at > now + 90
    ) {
      return session;
    }
    if (session?.refresh_token) {
      return await refreshSession(session.refresh_token);
    }
  } catch {
    await SecureStore.deleteItemAsync(SESSION_KEY);
  }
  return null;
}

export async function signOut(
  session: AuthSession | null
): Promise<void> {
  if (authConfigured && session?.access_token) {
    try {
      await authRequest(
        "/auth/v1/logout",
        {},
        session.access_token
      );
    } catch {
      // Local sign-out must still succeed even if the network is unavailable.
    }
  }
  await persistSession(null);
}
