module.exports = ({ config }) => {
  const production = process.env.EAS_BUILD_PROFILE === "production";

  if (production) {
    const required = [
      "EXPO_PUBLIC_API_URL",
      "EXPO_PUBLIC_SUPABASE_URL",
      "EXPO_PUBLIC_SUPABASE_ANON_KEY",
    ];
    const missing = required.filter((name) => !process.env[name]);
    if (missing.length) {
      throw new Error(
        `Production mobile build is missing: ${missing.join(", ")}`,
      );
    }

    if (
      process.env.EXPO_PUBLIC_API_URL.includes("localhost") ||
      process.env.EXPO_PUBLIC_API_URL.includes("127.0.0.1")
    ) {
      throw new Error(
        "Production EXPO_PUBLIC_API_URL must use the deployed HTTPS API.",
      );
    }
  }

  return config;
};
