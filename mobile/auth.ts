import "react-native-url-polyfill/auto";
import * as SecureStore from "expo-secure-store";
import { createClient, Session } from "@supabase/supabase-js";

const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL || "";
const SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY || "";

export const authConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);

const secureStorage = {
  getItem: (key: string) => SecureStore.getItemAsync(key),
  setItem: (key: string, value: string) => SecureStore.setItemAsync(key, value),
  removeItem: (key: string) => SecureStore.deleteItemAsync(key),
};

export const supabase = createClient(
  SUPABASE_URL || "https://placeholder.supabase.co",
  SUPABASE_ANON_KEY || "placeholder-anon-key",
  {
    auth: {
      storage: secureStorage,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,
    },
  }
);

export async function getAccessToken(): Promise<string | null> {
  if (!authConfigured) return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token || null;
}

export async function signIn(email: string, password: string) {
  return supabase.auth.signInWithPassword({ email, password });
}

export async function signUp(email: string, password: string) {
  return supabase.auth.signUp({ email, password });
}

export async function signOut() {
  return supabase.auth.signOut();
}

export async function getInitialSession(): Promise<Session | null> {
  if (!authConfigured) return null;
  const { data } = await supabase.auth.getSession();
  return data.session;
}