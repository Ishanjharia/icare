import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

const TOKEN_KEY = "icare_access_token";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err: AxiosError) => {
    if (err.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new Event("icare-auth-401"));
      if (!window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/register")) {
        window.location.assign("/login");
      }
    }
    return Promise.reject(err);
  },
);

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

/** WebSocket base (same host as page when using Vite proxy, else API origin). */
export function getWsBaseUrl(): string {
  const apiUrl = import.meta.env.VITE_API_URL as string | undefined;
  if (apiUrl && /^https?:\/\//i.test(apiUrl)) {
    const u = new URL(apiUrl);
    return u.protocol === "https:" ? `wss://${u.host}` : `ws://${u.host}`;
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}`;
}

/** HTTP origin for API (for EventSource when JWT is in query string). */
export function getApiOrigin(): string {
  const apiUrl = (import.meta.env.VITE_API_URL as string | undefined)?.trim();
  if (apiUrl && /^https?:\/\//i.test(apiUrl)) {
    try {
      return new URL(apiUrl).origin;
    } catch {
      return "";
    }
  }
  if (typeof window !== "undefined") {
    return window.location.origin;
  }
  return "";
}

export type ChatTurn = { role: "user" | "assistant"; content: string };

export function buildChatStreamUrl(params: {
  token: string;
  message: string;
  language: string;
  patientId?: string;
  history?: ChatTurn[];
}): string {
  const root = getApiOrigin();
  const url = new URL(`${root}/api/chat/stream`);
  url.searchParams.set("token", params.token);
  url.searchParams.set("message", params.message);
  url.searchParams.set("language", params.language);
  if (params.patientId?.trim()) {
    url.searchParams.set("patient_id", params.patientId.trim());
  }
  if (params.history?.length) {
    const slim = params.history.slice(-8).map((t) => ({ role: t.role, content: t.content.slice(0, 1500) }));
    const enc = JSON.stringify(slim);
    if (enc.length < 6000) {
      url.searchParams.set("history", enc);
    }
  }
  return url.toString();
}

// --- Types (mirror FastAPI) ---
export type UserRole = "patient" | "doctor" | "caregiver";

export type User = {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  language: string;
  phone: string | null;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type SymptomAnalyzeRequest = {
  symptoms_text: string;
  language?: string;
  include_vitals?: boolean;
  patient_id?: string | null;
};

export type SymptomAnalyzeResponse = {
  success: boolean;
  error: string | null;
  severity_level: string;
  urgent_care_needed: boolean;
  symptoms_summary: string;
  possible_conditions: string[];
  recommendations: string[];
  follow_up_questions: string[];
  confidence_score: number;
  medical_disclaimer: string;
  escalation_note: string | null;
  raw_context: Record<string, unknown> | null;
};

export type VitalReading = {
  metric: string;
  value: number;
  unit: string;
  timestamp: string;
  source: string;
};

export type VitalsSnapshot = {
  patient_id: string;
  readings: Record<string, VitalReading>;
};

export type VitalsHistoryPoint = { timestamp: string; value: number; unit?: string; metric?: string };

export type MetricThresholds = {
  warn_high?: number | null;
  alert_high?: number | null;
  critical_high?: number | null;
  warn_low?: number | null;
  critical_low?: number | null;
  alert_low?: number | null;
};

export type ThresholdConfig = {
  heart_rate?: MetricThresholds | null;
  spo2?: MetricThresholds | null;
  bp_systolic?: MetricThresholds | null;
  bp_diastolic?: MetricThresholds | null;
  steps?: MetricThresholds | null;
};

export type AlertOut = {
  id: string;
  patient_id: string;
  vital_type: string;
  value: number;
  threshold: number;
  level: number;
  message: string;
  acknowledged: boolean;
  acknowledged_at: string | null;
  sms_sent: boolean;
  caregiver_notified: boolean;
  created_at: string;
};

export type PipelineStep = {
  from_level: number;
  to_level: number;
  delay_seconds: number;
  action: string;
};

export type PipelineStatus = {
  patient_id: string;
  steps: PipelineStep[];
  active_alerts: AlertOut[];
};

export type HealthRecord = {
  id: number;
  patient_id: string;
  record_type: string;
  description: string;
  language: string;
  report_data: Record<string, unknown> | null;
  vitals_snapshot: Record<string, unknown> | null;
  created_at: string;
};

export type Prescription = {
  id: number;
  patient_id: string;
  doctor_id: string | null;
  doctor_name: string | null;
  medication: string;
  dosage: string;
  instructions: string;
  language: string;
  translated_text: string | null;
  created_at: string;
};

export type Appointment = {
  id: number;
  patient_id: string;
  doctor_id: string | null;
  doctor_name: string | null;
  appt_date: string;
  appt_time: string;
  status: string;
  language: string;
  notes: string | null;
  created_at: string;
};

export type Medication = {
  id: number;
  patient_id: string;
  name: string;
  dosage: string;
  frequency: string;
  start_date: string | null;
  end_date: string | null;
  status: string;
  notes: string | null;
  created_at: string;
};

// --- Auth ---
export async function healthCheck(): Promise<{ status: string; timestamp: string }> {
  const { data } = await api.get<{ status: string; timestamp: string }>("/health");
  return data;
}

export async function loginRequest(email: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/api/auth/login", { email, password });
  return data;
}

export async function registerRequest(payload: {
  name: string;
  email: string;
  password: string;
  role: UserRole;
  language: string;
  phone?: string | null;
}): Promise<User> {
  const { data } = await api.post<User>("/api/auth/register", payload);
  return data;
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get<User>("/api/auth/me");
  return data;
}

// --- Symptoms ---
export async function analyzeSymptoms(body: SymptomAnalyzeRequest): Promise<SymptomAnalyzeResponse> {
  const { data } = await api.post<SymptomAnalyzeResponse>("/api/symptoms/analyze", {
    ...body,
    include_vitals: body.include_vitals ?? true,
  });
  return data;
}

export async function fetchSymptomAnalysisHistory(patientId: string): Promise<HealthRecord[]> {
  const { data } = await api.get<HealthRecord[]>(`/api/symptoms/history/${patientId}`);
  return data;
}

export type HospitalSearchBody = { city: string; specialty?: string | null; language?: string };

export type HospitalSearchResult = {
  success: boolean;
  error: string | null;
  hospitals: Record<string, unknown>[];
};

export async function searchHospitals(body: HospitalSearchBody): Promise<HospitalSearchResult> {
  const { data } = await api.post<HospitalSearchResult>("/api/hospitals/search", {
    city: body.city,
    specialty: body.specialty ?? null,
    language: body.language ?? "English",
  });
  return data;
}

export async function fetchSavedHospitals(userId: string): Promise<{ id: number; user_id: string; hospital: Record<string, unknown>; created_at: string }[]> {
  const { data } = await api.get(`/api/hospitals/saved/${userId}`);
  return data;
}

export async function saveHospital(userId: string, hospital: Record<string, unknown>): Promise<{ id: number; user_id: string; hospital: Record<string, unknown>; created_at: string }> {
  const { data } = await api.post(`/api/hospitals/saved/${userId}`, { hospital });
  return data;
}

/** POST /api/chat/message — read SSE body with fetch (Bearer auth). */
export async function streamChatMessage(
  body: {
    message: string;
    language: string;
    conversation_history: ChatTurn[];
    patient_id?: string | null;
  },
  onChunk: (text: string) => void,
): Promise<void> {
  const root = getApiOrigin();
  const token = getStoredToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${root}/api/chat/message`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      message: body.message,
      language: body.language,
      conversation_history: body.conversation_history,
      patient_id: body.patient_id ?? null,
    }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`Chat stream failed: ${res.status}`);
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += dec.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      for (const line of block.split("\n")) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (raw === '"[DONE]"' || raw === "[DONE]") return;
        try {
          const piece = JSON.parse(raw) as string;
          if (typeof piece === "string") onChunk(piece);
        } catch {
          onChunk(raw);
        }
      }
    }
  }
}

// --- Voice (REST helpers for symptom flow) ---
export async function transcribeVoiceAudio(audio: Blob): Promise<{
  success: boolean;
  transcription: string;
  detected_language?: string;
  error?: string;
}> {
  const form = new FormData();
  form.append("audio", audio, "recording.webm");
  const { data } = await api.post("/api/voice/transcribe", form);
  return data;
}

// --- Vitals ---
export async function fetchVitalsSnapshot(patientId: string): Promise<VitalsSnapshot> {
  const { data } = await api.get<VitalsSnapshot>(`/api/vitals/snapshot/${patientId}`);
  return data;
}

export async function fetchVitalsHistory(
  patientId: string,
  metric: string,
  hours: number,
): Promise<VitalsHistoryPoint[]> {
  const { data } = await api.get<VitalsHistoryPoint[]>(`/api/vitals/history/${patientId}`, {
    params: { metric, hours },
  });
  return data;
}

export async function fetchThresholds(patientId: string): Promise<ThresholdConfig> {
  const { data } = await api.get<ThresholdConfig>(`/api/vitals/thresholds/${patientId}`);
  return data;
}

export type VitalsScenario = "normal" | "hr_spike" | "spo2_drop" | "bp_high";

export async function ingestVitalReading(patientId: string, reading: VitalReading): Promise<{ status: string }> {
  const { data } = await api.post<{ status: string }>("/api/vitals/ingest", {
    patient_id: patientId,
    reading,
  });
  return data;
}

export async function startVitalsSimulation(body: {
  patient_id: string;
  scenario: VitalsScenario;
  duration_seconds?: number;
}): Promise<{ status: string; patient_id: string; scenario: string; duration_seconds: number }> {
  const { data } = await api.post("/api/vitals/simulate", {
    patient_id: body.patient_id,
    scenario: body.scenario,
    duration_seconds: body.duration_seconds ?? 60,
  });
  return data;
}

// --- Alerts ---
export async function fetchActiveAlerts(patientId: string): Promise<AlertOut[]> {
  const { data } = await api.get<AlertOut[]>(`/api/alerts/${patientId}`);
  return data;
}

export async function fetchAlertPipeline(patientId: string): Promise<PipelineStatus> {
  const { data } = await api.get<PipelineStatus>(`/api/alerts/${patientId}/pipeline`);
  return data;
}

export async function acknowledgeAlert(alertId: string): Promise<void> {
  await api.post(`/api/alerts/${alertId}/acknowledge`);
}

// --- Records ---
export async function fetchHealthContext(patientId: string): Promise<Record<string, unknown>> {
  const { data } = await api.get<Record<string, unknown>>(`/api/records/${patientId}/health-context`);
  return data;
}

export async function fetchHealthRecords(patientId: string): Promise<HealthRecord[]> {
  const { data } = await api.get<HealthRecord[]>(`/api/records/${patientId}`);
  return data;
}

export async function createHealthRecord(
  patientId: string,
  body: {
    record_type: string;
    description: string;
    language?: string;
    report_data?: Record<string, unknown> | null;
    vitals_snapshot?: Record<string, unknown> | null;
  },
): Promise<HealthRecord> {
  const { data } = await api.post<HealthRecord>(`/api/records/${patientId}`, body);
  return data;
}

// --- Prescriptions ---
export async function fetchPrescriptions(patientId: string): Promise<Prescription[]> {
  const { data } = await api.get<Prescription[]>(`/api/prescriptions/${patientId}`);
  return data;
}

export async function createPrescription(body: {
  patient_id: string;
  doctor_id?: string | null;
  doctor_name?: string | null;
  medication: string;
  dosage: string;
  instructions: string;
  language?: string;
  translated_text?: string | null;
}): Promise<Prescription> {
  const { data } = await api.post<Prescription>("/api/prescriptions/", body);
  return data;
}

export async function fetchPrescriptionPdfBlob(prescriptionId: number): Promise<Blob> {
  const { data } = await api.get<Blob>(`/api/prescriptions/${prescriptionId}/pdf`, {
    responseType: "blob",
  });
  return data;
}

// --- Appointments ---
export async function fetchAppointments(patientId: string): Promise<Appointment[]> {
  const { data } = await api.get<Appointment[]>(`/api/appointments/${patientId}`);
  return data;
}

export async function createAppointment(body: {
  patient_id: string;
  doctor_id?: string | null;
  doctor_name?: string | null;
  appt_date: string;
  appt_time: string;
  status?: string;
  language?: string;
  notes?: string | null;
}): Promise<Appointment> {
  const { data } = await api.post<Appointment>("/api/appointments/", body);
  return data;
}

// --- Medications ---
export async function fetchMedications(patientId: string): Promise<Medication[]> {
  const { data } = await api.get<Medication[]>(`/api/medications/${patientId}`);
  return data;
}

export async function createMedication(body: {
  patient_id: string;
  name: string;
  dosage: string;
  frequency: string;
  start_date?: string | null;
  end_date?: string | null;
  status?: string;
  notes?: string | null;
}): Promise<Medication> {
  const { data } = await api.post<Medication>("/api/medications/", body);
  return data;
}

export async function updateMedication(
  id: number,
  body: Partial<{
    name: string;
    dosage: string;
    frequency: string;
    start_date: string | null;
    end_date: string | null;
    status: string;
    notes: string | null;
  }>,
): Promise<Medication> {
  const { data } = await api.put<Medication>(`/api/medications/${id}`, body);
  return data;
}
