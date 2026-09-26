import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const appJsonPath = path.join(root, "app.json");
const easJsonPath = path.join(root, "eas.json");

function fail(message) {
  console.error(`RELEASE CHECK FAILED: ${message}`);
  process.exitCode = 1;
}

function requireHttps(name, value) {
  if (!value) {
    fail(`${name} is required for store builds.`);
    return;
  }
  if (!value.startsWith("https://")) {
    fail(`${name} must use HTTPS for store builds.`);
  }
}

const appJson = JSON.parse(fs.readFileSync(appJsonPath, "utf8"));
const easJson = JSON.parse(fs.readFileSync(easJsonPath, "utf8"));
const expo = appJson.expo || {};
const ios = expo.ios || {};
const android = expo.android || {};
const production = easJson.build?.production || {};

const apiUrl = (process.env.EXPO_PUBLIC_API_URL || "").trim();
const supabaseUrl = (process.env.EXPO_PUBLIC_SUPABASE_URL || "").trim();
const supabaseAnonKey = (process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY || "").trim();

requireHttps("EXPO_PUBLIC_API_URL", apiUrl);
requireHttps("EXPO_PUBLIC_SUPABASE_URL", supabaseUrl);

if (!supabaseAnonKey) {
  fail("EXPO_PUBLIC_SUPABASE_ANON_KEY is required for store builds.");
}

if (!ios.bundleIdentifier) {
  fail("iOS bundleIdentifier is missing from app.json.");
}
if (!android.package) {
  fail("Android package is missing from app.json.");
}
if (ios.bundleIdentifier !== android.package) {
  fail("iOS bundleIdentifier and Android package must match for the current release convention.");
}
if (!/^com\.[a-z0-9][a-z0-9.-]+$/i.test(ios.bundleIdentifier || "")) {
  fail("Bundle identifier/package format is invalid.");
}
if (!expo.version || !/^\d+\.\d+\.\d+$/.test(expo.version)) {
  fail("Expo app version must be semantic x.y.z.");
}
if (!expo.scheme) {
  fail("Deep-link scheme is required.");
}
if (production.distribution !== "store") {
  fail("EAS production build must use distribution=store.");
}
if (production.autoIncrement !== true) {
  fail("EAS production build must enable autoIncrement.");
}
if (!easJson.submit?.production) {
  fail("EAS submit.production profile is missing.");
}

if (!process.exitCode) {
  console.log("Store release configuration check passed.");
  console.log(`App: ${expo.name} ${expo.version}`);
  console.log(`Bundle/package: ${ios.bundleIdentifier}`);
  console.log(`API: ${apiUrl}`);
}
