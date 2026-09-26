import { StatusBar } from "expo-status-bar";
import * as DocumentPicker from "expo-document-picker";
import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

const API_URL =
  process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";

type Project = {
  id: string;
  name: string;
  location?: string | null;
  client?: string | null;
  opportunity_number?: string | null;
  phase: string;
  status: string;
  updated_at?: string;
};

type Finding = {
  severity?: string;
  status?: string;
  category?: string;
  title?: string;
  why_it_matters?: string;
  recommended_action?: string;
};

type DrawingAnalysis = {
  id: string;
  file_name: string;
  page_count: number;
  register?: {
    sheet_count?: number;
    rooms?: string[];
  };
  qa?: {
    finding_count?: number;
    findings?: Finding[];
    connection_graph?: {
      node_count?: number;
      edge_count?: number;
      resolved_edge_count?: number;
      ambiguous_edge_count?: number;
    };
  };
  created_at: string;
};

type ProgressEntry = {
  id: string;
  date: string;
  phase?: string | null;
  completed?: string[];
  issues?: string[];
  blockers?: string[];
  next_actions?: string[];
  notes?: string | null;
};

type ReportItem = {
  id: string;
  period: string;
  anchor_date: string;
  payload?: Record<string, unknown>;
  created_at: string;
};

type Snapshot = {
  project: Project;
  progress_entries: ProgressEntry[];
  drawing_analyses: DrawingAnalysis[];
  reports: ReportItem[];
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  const payload = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    const detail =
      typeof payload?.detail === "string"
        ? payload.detail
        : payload?.detail?.message || "Request failed.";
    throw new Error(detail);
  }
  return payload as T;
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [newProjectName, setNewProjectName] = useState("");
  const [newLocation, setNewLocation] = useState("");
  const [progressNote, setProgressNote] = useState("");
  const [issueNote, setIssueNote] = useState("");
  const [nextAction, setNextAction] = useState("");
  const [loading, setLoading] = useState(false);
  const [busyLabel, setBusyLabel] = useState("");
  const [error, setError] = useState("");

  const currentProject = useMemo(
    () => snapshot?.project || projects.find((p) => p.id === selectedId) || null,
    [projects, selectedId, snapshot]
  );

  const loadProjects = async () => {
    setError("");
    try {
      const data = await api<{ projects: Project[] }>("/v1/projects");
      setProjects(data.projects || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load projects.");
    }
  };

  const loadSnapshot = async (projectId: string) => {
    setError("");
    try {
      const data = await api<Snapshot>(`/v1/projects/${projectId}`);
      setSnapshot(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load project.");
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (selectedId) loadSnapshot(selectedId);
    else setSnapshot(null);
  }, [selectedId]);

  const createProject = async () => {
    if (!newProjectName.trim()) return;
    setLoading(true);
    setBusyLabel("Creating project");
    setError("");
    try {
      const created = await api<Project>("/v1/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newProjectName.trim(),
          location: newLocation.trim() || null,
          phase: "Design Review / Pre-Start",
        }),
      });
      setNewProjectName("");
      setNewLocation("");
      await loadProjects();
      setSelectedId(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create project.");
    } finally {
      setLoading(false);
      setBusyLabel("");
    }
  };

  const uploadDrawing = async () => {
    if (!selectedId) return;

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
    setBusyLabel("Analyzing full drawing set");
    setError("");
    try {
      await api(`/v1/projects/${selectedId}/drawings/qa`, {
        method: "POST",
        body: form,
      });
      await loadSnapshot(selectedId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Drawing analysis failed.");
    } finally {
      setLoading(false);
      setBusyLabel("");
    }
  };

  const addProgress = async () => {
    if (!selectedId || (!progressNote.trim() && !issueNote.trim() && !nextAction.trim())) {
      return;
    }

    setLoading(true);
    setBusyLabel("Saving project progress");
    setError("");
    try {
      await api(`/v1/projects/${selectedId}/progress`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date: todayIso(),
          phase: currentProject?.phase || "Design Review / Pre-Start",
          completed: progressNote.trim() ? [progressNote.trim()] : [],
          issues: issueNote.trim() ? [issueNote.trim()] : [],
          next_actions: nextAction.trim() ? [nextAction.trim()] : [],
        }),
      });
      setProgressNote("");
      setIssueNote("");
      setNextAction("");
      await loadSnapshot(selectedId);
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save progress.");
    } finally {
      setLoading(false);
      setBusyLabel("");
    }
  };

  const generateReport = async (period: "daily" | "weekly" | "monthly") => {
    if (!selectedId) return;
    setLoading(true);
    setBusyLabel(`Generating ${period} report`);
    setError("");
    try {
      await api(`/v1/projects/${selectedId}/reports/${period}`, {
        method: "POST",
      });
      await loadSnapshot(selectedId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate report.");
    } finally {
      setLoading(false);
      setBusyLabel("");
    }
  };

  if (!selectedId) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <StatusBar style="light" />
        <ScrollView contentContainerStyle={styles.container}>
          <Text style={styles.eyebrow}>PROFESSIONAL AV / UC</Text>
          <Text style={styles.title}>AV Intelligence Assistant</Text>
          <Text style={styles.subtitle}>
            Project engineering from drawing review and first fix to commissioning and handover.
          </Text>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>New Project</Text>
            <TextInput
              value={newProjectName}
              onChangeText={setNewProjectName}
              placeholder="Project name"
              placeholderTextColor="#64748B"
              style={styles.input}
            />
            <TextInput
              value={newLocation}
              onChangeText={setNewLocation}
              placeholder="Location (optional)"
              placeholderTextColor="#64748B"
              style={styles.input}
            />
            <TouchableOpacity
              style={styles.primaryButton}
              onPress={createProject}
              disabled={loading || !newProjectName.trim()}
            >
              <Text style={styles.primaryButtonText}>Create Project</Text>
            </TouchableOpacity>
          </View>

          <Text style={styles.sectionTitle}>Projects</Text>
          {projects.length === 0 ? (
            <Text style={styles.muted}>No projects yet.</Text>
          ) : (
            projects.map((project) => (
              <TouchableOpacity
                key={project.id}
                style={styles.projectCard}
                onPress={() => setSelectedId(project.id)}
              >
                <View style={styles.projectHeader}>
                  <Text style={styles.projectName}>{project.name}</Text>
                  <Text style={styles.status}>{project.status.toUpperCase()}</Text>
                </View>
                <Text style={styles.muted}>{project.location || "Location not set"}</Text>
                <Text style={styles.phase}>{project.phase}</Text>
              </TouchableOpacity>
            ))
          )}

          {!!error && <Text style={styles.error}>{error}</Text>}
        </ScrollView>
      </SafeAreaView>
    );
  }

  const latestDrawing = snapshot?.drawing_analyses?.[0];
  const findings = latestDrawing?.qa?.findings || [];
  const graph = latestDrawing?.qa?.connection_graph;

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="light" />
      <ScrollView contentContainerStyle={styles.container}>
        <TouchableOpacity onPress={() => setSelectedId(null)}>
          <Text style={styles.back}>‹ All Projects</Text>
        </TouchableOpacity>

        <Text style={styles.eyebrow}>PROJECT WORKSPACE</Text>
        <Text style={styles.title}>{currentProject?.name || "Project"}</Text>
        <Text style={styles.subtitle}>
          {currentProject?.location || "Location not set"} · {currentProject?.phase}
        </Text>

        <View style={styles.statsRow}>
          <View style={styles.stat}>
            <Text style={styles.statValue}>{snapshot?.drawing_analyses?.length || 0}</Text>
            <Text style={styles.statLabel}>Drawings</Text>
          </View>
          <View style={styles.stat}>
            <Text style={styles.statValue}>{snapshot?.progress_entries?.length || 0}</Text>
            <Text style={styles.statLabel}>Updates</Text>
          </View>
          <View style={styles.stat}>
            <Text style={styles.statValue}>{snapshot?.reports?.length || 0}</Text>
            <Text style={styles.statLabel}>Reports</Text>
          </View>
        </View>

        <TouchableOpacity
          style={styles.primaryButton}
          onPress={uploadDrawing}
          disabled={loading}
        >
          <Text style={styles.primaryButtonText}>Upload & Review AV Drawing Set</Text>
        </TouchableOpacity>

        {loading && (
          <View style={styles.loadingRow}>
            <ActivityIndicator color="#68A7FF" />
            <Text style={styles.loadingText}>{busyLabel}</Text>
          </View>
        )}
        {!!error && <Text style={styles.error}>{error}</Text>}

        {latestDrawing && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Latest Drawing QA</Text>
            <Text style={styles.metric}>
              {latestDrawing.file_name} · {latestDrawing.page_count} pages
            </Text>

            {!!graph && (
              <View style={styles.graphRow}>
                <Text style={styles.graphMetric}>{graph.node_count || 0} devices</Text>
                <Text style={styles.graphMetric}>{graph.edge_count || 0} wires</Text>
                <Text style={styles.graphMetric}>{graph.resolved_edge_count || 0} resolved</Text>
                <Text style={styles.graphMetric}>{graph.ambiguous_edge_count || 0} verify</Text>
              </View>
            )}

            <Text style={styles.sectionTitle}>Engineering Findings</Text>
            {findings.length === 0 ? (
              <Text style={styles.muted}>No extracted QA findings.</Text>
            ) : (
              findings.slice(0, 12).map((item, index) => (
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
          </View>
        )}

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Today’s Progress</Text>
          <TextInput
            value={progressNote}
            onChangeText={setProgressNote}
            placeholder="Completed work"
            placeholderTextColor="#64748B"
            style={styles.input}
            multiline
          />
          <TextInput
            value={issueNote}
            onChangeText={setIssueNote}
            placeholder="Issue or blocker"
            placeholderTextColor="#64748B"
            style={styles.input}
            multiline
          />
          <TextInput
            value={nextAction}
            onChangeText={setNextAction}
            placeholder="Next action"
            placeholderTextColor="#64748B"
            style={styles.input}
            multiline
          />
          <TouchableOpacity style={styles.secondaryButton} onPress={addProgress} disabled={loading}>
            <Text style={styles.secondaryButtonText}>Save Progress Update</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Reports</Text>
          <View style={styles.reportButtons}>
            {(["daily", "weekly", "monthly"] as const).map((period) => (
              <TouchableOpacity
                key={period}
                style={styles.reportButton}
                onPress={() => generateReport(period)}
                disabled={loading}
              >
                <Text style={styles.reportButtonText}>
                  {period.charAt(0).toUpperCase() + period.slice(1)}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {(snapshot?.reports || []).slice(0, 5).map((report) => (
            <View style={styles.reportRow} key={report.id}>
              <Text style={styles.reportTitle}>{report.period.toUpperCase()}</Text>
              <Text style={styles.muted}>{report.anchor_date}</Text>
            </View>
          ))}
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Recent Progress</Text>
          {(snapshot?.progress_entries || []).length === 0 ? (
            <Text style={styles.muted}>No progress updates yet.</Text>
          ) : (
            [...(snapshot?.progress_entries || [])]
              .reverse()
              .slice(0, 8)
              .map((entry) => (
                <View style={styles.progressRow} key={entry.id}>
                  <Text style={styles.progressDate}>{entry.date}</Text>
                  {(entry.completed || []).map((item) => (
                    <Text key={item} style={styles.row}>✓ {item}</Text>
                  ))}
                  {(entry.issues || []).map((item) => (
                    <Text key={item} style={styles.issue}>! {item}</Text>
                  ))}
                  {(entry.next_actions || []).map((item) => (
                    <Text key={item} style={styles.next}>→ {item}</Text>
                  ))}
                </View>
              ))
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#07101D" },
  container: {
    flexGrow: 1,
    paddingHorizontal: 20,
    paddingTop: 46,
    paddingBottom: 50,
  },
  eyebrow: {
    color: "#68A7FF",
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.8,
    marginBottom: 10,
  },
  title: { color: "#FFFFFF", fontSize: 32, lineHeight: 38, fontWeight: "800" },
  subtitle: { color: "#A8B3C7", fontSize: 15, lineHeight: 22, marginTop: 10, marginBottom: 22 },
  back: { color: "#80B5FF", fontSize: 16, marginBottom: 22 },
  card: {
    marginTop: 18,
    borderRadius: 20,
    padding: 17,
    backgroundColor: "#111D2E",
    borderWidth: 1,
    borderColor: "#20324D",
  },
  cardTitle: { color: "#FFFFFF", fontSize: 19, fontWeight: "800", marginBottom: 10 },
  input: {
    color: "#FFFFFF",
    backgroundColor: "#0A1524",
    borderWidth: 1,
    borderColor: "#253955",
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 13,
    marginTop: 10,
    minHeight: 48,
  },
  primaryButton: {
    minHeight: 54,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#2E7CF6",
    paddingHorizontal: 18,
    marginTop: 14,
  },
  primaryButtonText: { color: "#FFFFFF", fontWeight: "700", fontSize: 15 },
  secondaryButton: {
    minHeight: 50,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "#3B82F6",
    marginTop: 14,
  },
  secondaryButtonText: { color: "#80B5FF", fontWeight: "700" },
  sectionTitle: { color: "#FFFFFF", fontWeight: "700", fontSize: 15, marginTop: 22, marginBottom: 9 },
  projectCard: {
    backgroundColor: "#111D2E",
    borderColor: "#20324D",
    borderWidth: 1,
    borderRadius: 18,
    padding: 16,
    marginBottom: 12,
  },
  projectHeader: { flexDirection: "row", justifyContent: "space-between", gap: 8 },
  projectName: { color: "#FFFFFF", fontSize: 17, fontWeight: "750", flex: 1 },
  status: { color: "#65D6A8", fontSize: 10, fontWeight: "800" },
  phase: { color: "#80B5FF", marginTop: 8, fontSize: 13 },
  muted: { color: "#8FA4C2", lineHeight: 20 },
  error: { color: "#FF8A8A", marginTop: 15, lineHeight: 20 },
  loadingRow: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: 14 },
  loadingText: { color: "#A8B3C7" },
  statsRow: { flexDirection: "row", gap: 10, marginBottom: 5 },
  stat: {
    flex: 1,
    backgroundColor: "#111D2E",
    borderRadius: 15,
    paddingVertical: 13,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#20324D",
  },
  statValue: { color: "#FFFFFF", fontSize: 20, fontWeight: "800" },
  statLabel: { color: "#8FA4C2", fontSize: 11, marginTop: 3 },
  metric: { color: "#8FA4C2", lineHeight: 20 },
  graphRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12 },
  graphMetric: {
    color: "#C8D8EF",
    backgroundColor: "#16263B",
    borderRadius: 10,
    paddingVertical: 6,
    paddingHorizontal: 8,
    fontSize: 11,
  },
  finding: {
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#2B3B52",
  },
  findingBadge: { color: "#FFB86B", fontSize: 10, fontWeight: "800", letterSpacing: 0.5 },
  findingTitle: { color: "#FFFFFF", fontSize: 15, fontWeight: "700", marginTop: 5 },
  findingText: { color: "#C4CFDF", marginTop: 4, lineHeight: 19 },
  findingAction: { color: "#8CC6FF", marginTop: 6, lineHeight: 19 },
  reportButtons: { flexDirection: "row", gap: 8, marginTop: 4 },
  reportButton: {
    flex: 1,
    backgroundColor: "#16263B",
    borderRadius: 12,
    paddingVertical: 11,
    alignItems: "center",
  },
  reportButtonText: { color: "#8CC6FF", fontWeight: "700", fontSize: 12 },
  reportRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 11,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#2B3B52",
  },
  reportTitle: { color: "#FFFFFF", fontWeight: "700" },
  progressRow: {
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#2B3B52",
  },
  progressDate: { color: "#8FA4C2", fontSize: 12, marginBottom: 5 },
  row: { color: "#CDD6E4", marginBottom: 4, lineHeight: 19 },
  issue: { color: "#FFB86B", marginBottom: 4, lineHeight: 19 },
  next: { color: "#80B5FF", marginBottom: 4, lineHeight: 19 },
});
