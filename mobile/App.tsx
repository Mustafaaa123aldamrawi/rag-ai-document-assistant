import { StatusBar } from "expo-status-bar";
import * as DocumentPicker from "expo-document-picker";
import React, { useMemo, useState } from "react";
import {
  ActivityIndicator,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

const API_URL =
  process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";

type DrawingResult = {
  file_name: string;
  page_count: number;
  qa?: {
    finding_count?: number;
    findings?: Array<{
      severity?: string;
      status?: string;
      category?: string;
      title?: string;
      why_it_matters?: string;
      recommended_action?: string;
    }>;
    programming_requirements?: Array<{
      vendor?: string;
      models_detected?: string[];
      programming_scope?: string;
      engineering_tool?: string;
      status?: string;
    }>;
  };
  register: {
    project?: {
      project_name?: string | null;
      location?: string | null;
      opportunity_number?: string | null;
    };
    sheet_count?: number;
    rooms?: string[];
    coordination_requirements?: Array<{
      category?: string;
      requirement?: string;
    }>;
    risk_flags?: Array<{
      type?: string;
      message?: string;
      page_number?: number;
    }>;
  };
};

export default function App() {
  const [result, setResult] = useState<DrawingResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const projectTitle = useMemo(
    () =>
      result?.register?.project?.project_name ||
      "AV Intelligence Assistant",
    [result]
  );

  const pickDrawing = async () => {
    setError("");
    const picked = await DocumentPicker.getDocumentAsync({
      type: "application/pdf",
      copyToCacheDirectory: true,
      multiple: false,
    });

    if (picked.canceled || !picked.assets?.[0]) return;

    const asset = picked.assets[0];
    const form = new FormData();
    form.append(
      "file",
      {
        uri: asset.uri,
        name: asset.name || "drawing.pdf",
        type: asset.mimeType || "application/pdf",
      } as any
    );

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/v1/drawings/qa`, {
        method: "POST",
        body: form,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || "Drawing analysis failed.");
      }
      setResult(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to analyze drawing.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="light" />
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.eyebrow}>PROFESSIONAL AV / UC</Text>
        <Text style={styles.title}>{projectTitle}</Text>
        <Text style={styles.subtitle}>
          From drawing review and first fix to commissioning, reporting, and handover.
        </Text>

        <TouchableOpacity
          style={styles.primaryButton}
          onPress={pickDrawing}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.primaryButtonText}>Analyze AV Drawing Set</Text>
          )}
        </TouchableOpacity>

        {!!error && <Text style={styles.error}>{error}</Text>}

        {result && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Project Intelligence</Text>
            <Text style={styles.metric}>
              {result.page_count} pages · {result.register?.sheet_count || 0} indexed sheets
            </Text>

            <Text style={styles.sectionTitle}>Rooms / Areas</Text>
            {(result.register?.rooms || []).slice(0, 12).map((room) => (
              <Text style={styles.row} key={room}>• {room}</Text>
            ))}

            <Text style={styles.sectionTitle}>Coordination Requirements</Text>
            {(result.register?.coordination_requirements || [])
              .slice(0, 8)
              .map((item, index) => (
                <View style={styles.requirement} key={`${item.category}-${index}`}>
                  <Text style={styles.requirementTitle}>{item.category}</Text>
                  <Text style={styles.requirementText}>{item.requirement}</Text>
                </View>
              ))}
            <Text style={styles.sectionTitle}>Engineering Findings</Text>
            {(result.qa?.findings || []).length === 0 ? (
              <Text style={styles.row}>No text-extraction QA findings detected.</Text>
            ) : (
              (result.qa?.findings || []).slice(0, 10).map((item, index) => (
                <View style={styles.finding} key={`${item.category}-${index}`}>
                  <Text style={styles.findingBadge}>
                    {(item.severity || "verify").toUpperCase()} · {item.status || "VERIFY"}
                  </Text>
                  <Text style={styles.findingTitle}>{item.title}</Text>
                  {!!item.why_it_matters && (
                    <Text style={styles.findingText}>{item.why_it_matters}</Text>
                  )}
                  {!!item.recommended_action && (
                    <Text style={styles.findingAction}>Next: {item.recommended_action}</Text>
                  )}
                </View>
              ))
            )}

            <Text style={styles.sectionTitle}>Programming Scope</Text>
            {(result.qa?.programming_requirements || []).length === 0 ? (
              <Text style={styles.row}>No supported vendor programming scope detected yet.</Text>
            ) : (
              (result.qa?.programming_requirements || []).map((item, index) => (
                <View style={styles.requirement} key={`${item.vendor}-${index}`}>
                  <Text style={styles.requirementTitle}>{item.vendor}</Text>
                  <Text style={styles.requirementText}>{item.programming_scope}</Text>
                  <Text style={styles.toolText}>{item.engineering_tool}</Text>
                </View>
              ))
            )}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#07101D",
  },
  container: {
    flexGrow: 1,
    paddingHorizontal: 22,
    paddingTop: 56,
    paddingBottom: 40,
  },
  eyebrow: {
    color: "#68A7FF",
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.8,
    marginBottom: 12,
  },
  title: {
    color: "#FFFFFF",
    fontSize: 34,
    lineHeight: 40,
    fontWeight: "800",
  },
  subtitle: {
    color: "#A8B3C7",
    fontSize: 16,
    lineHeight: 24,
    marginTop: 12,
    marginBottom: 28,
  },
  primaryButton: {
    minHeight: 54,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#2E7CF6",
    paddingHorizontal: 18,
  },
  primaryButtonText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 16,
  },
  error: {
    color: "#FF8A8A",
    marginTop: 16,
    lineHeight: 20,
  },
  card: {
    marginTop: 24,
    borderRadius: 20,
    padding: 18,
    backgroundColor: "#111D2E",
    borderWidth: 1,
    borderColor: "#20324D",
  },
  cardTitle: {
    color: "#FFFFFF",
    fontSize: 20,
    fontWeight: "800",
  },
  metric: {
    color: "#8FA4C2",
    marginTop: 6,
    marginBottom: 18,
  },
  sectionTitle: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 15,
    marginTop: 16,
    marginBottom: 8,
  },
  row: {
    color: "#CDD6E4",
    marginBottom: 5,
    lineHeight: 20,
  },
  finding: {
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#2B3B52",
  },
  findingBadge: {
    color: "#FFB86B",
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 0.6,
  },
  findingTitle: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "700",
    marginTop: 5,
  },
  findingText: {
    color: "#C4CFDF",
    marginTop: 4,
    lineHeight: 19,
  },
  findingAction: {
    color: "#8CC6FF",
    marginTop: 6,
    lineHeight: 19,
  },
  toolText: {
    color: "#8FA4C2",
    marginTop: 4,
    fontSize: 12,
  },
  requirement: {
    paddingVertical: 9,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#2B3B52",
  },
  requirementTitle: {
    color: "#80B5FF",
    fontWeight: "700",
  },
  requirementText: {
    color: "#C4CFDF",
    marginTop: 3,
    lineHeight: 19,
  },
});
