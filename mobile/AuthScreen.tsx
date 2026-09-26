import React, { useState } from "react";
import {
  ActivityIndicator,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { authConfigured, supabase } from "./supabase";

export function AuthScreen() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const submit = async () => {
    if (!supabase || !email.trim() || password.length < 6) return;
    setBusy(true);
    setMessage("");
    try {
      if (mode === "signin") {
        const { error } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });
        if (error) throw error;
      } else {
        const { data, error } = await supabase.auth.signUp({
          email: email.trim(),
          password,
        });
        if (error) throw error;
        if (!data.session) {
          setMessage("Check your email to confirm your account, then sign in.");
        }
      }
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Authentication failed.",
      );
    } finally {
      setBusy(false);
    }
  };

  if (!authConfigured) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.container}>
          <Text style={styles.eyebrow}>AV INTELLIGENCE ASSISTANT</Text>
          <Text style={styles.title}>Authentication setup required</Text>
          <Text style={styles.message}>
            Configure EXPO_PUBLIC_SUPABASE_URL and
            EXPO_PUBLIC_SUPABASE_ANON_KEY for the mobile build.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.eyebrow}>PROFESSIONAL AV / UC</Text>
        <Text style={styles.title}>AV Intelligence Assistant</Text>
        <Text style={styles.subtitle}>
          Secure project engineering from drawing review to handover.
        </Text>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>
            {mode === "signin" ? "Sign in" : "Create account"}
          </Text>
          <TextInput
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            value={email}
            onChangeText={setEmail}
            placeholder="Email"
            placeholderTextColor="#64748B"
            style={styles.input}
          />
          <TextInput
            secureTextEntry
            value={password}
            onChangeText={setPassword}
            placeholder="Password"
            placeholderTextColor="#64748B"
            style={styles.input}
          />
          <TouchableOpacity
            style={styles.primary}
            onPress={submit}
            disabled={busy || !email.trim() || password.length < 6}
          >
            {busy ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.primaryText}>
                {mode === "signin" ? "Sign in" : "Create account"}
              </Text>
            )}
          </TouchableOpacity>

          {!!message && <Text style={styles.message}>{message}</Text>}

          <TouchableOpacity
            onPress={() =>
              setMode(mode === "signin" ? "signup" : "signin")
            }
          >
            <Text style={styles.switchText}>
              {mode === "signin"
                ? "New here? Create an account"
                : "Already have an account? Sign in"}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#07101D" },
  container: { flex: 1, paddingHorizontal: 22, paddingTop: 70 },
  eyebrow: {
    color: "#68A7FF",
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.8,
  },
  title: {
    color: "#FFFFFF",
    fontSize: 32,
    lineHeight: 39,
    fontWeight: "800",
    marginTop: 12,
  },
  subtitle: {
    color: "#A8B3C7",
    fontSize: 15,
    lineHeight: 22,
    marginTop: 10,
  },
  card: {
    marginTop: 30,
    padding: 18,
    borderRadius: 20,
    backgroundColor: "#111D2E",
    borderWidth: 1,
    borderColor: "#20324D",
  },
  cardTitle: {
    color: "#FFFFFF",
    fontSize: 21,
    fontWeight: "800",
    marginBottom: 8,
  },
  input: {
    color: "#FFFFFF",
    backgroundColor: "#0A1524",
    borderWidth: 1,
    borderColor: "#253955",
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 13,
    marginTop: 10,
    minHeight: 50,
  },
  primary: {
    minHeight: 52,
    borderRadius: 14,
    backgroundColor: "#2E7CF6",
    justifyContent: "center",
    alignItems: "center",
    marginTop: 16,
  },
  primaryText: { color: "#FFFFFF", fontWeight: "800" },
  message: { color: "#FFB86B", lineHeight: 20, marginTop: 14 },
  switchText: {
    color: "#80B5FF",
    fontWeight: "700",
    textAlign: "center",
    marginTop: 18,
  },
});
