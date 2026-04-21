import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "../hooks/useAuth";
import {
  ingestVitalReading,
  startVitalsSimulation,
  type VitalReading,
  type VitalsScenario,
} from "../services/api";

const SCENARIOS: { value: VitalsScenario; label: string; hint: string }[] = [
  { value: "normal", label: "Normal", hint: "HR ~75, SpO₂ ~98, BP ~120/80 (small random walk)." },
  {
    value: "hr_spike",
    label: "HR spike",
    hint: "HR ramps to ~145 over 30s (crosses warn 100 bpm and alert 130 bpm thresholds).",
  },
  { value: "spo2_drop", label: "SpO₂ drop", hint: "SpO₂ falls to ~89% over 20s (low SpO₂ alert / critical bands)." },
  { value: "bp_high", label: "BP high", hint: "Systolic ramps toward ~168 over 30s (elevated BP warnings)." },
];

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

function buildReadings(scenario: VitalsScenario, elapsedSec: number): VitalReading[] {
  const ts = new Date().toISOString();
  const source = "web_simulator";

  if (scenario === "normal") {
    const hr = clamp(75 + (Math.random() - 0.5) * 10, 62, 95);
    const spo2 = clamp(98 + (Math.random() - 0.5) * 2.5, 94, 100);
    const sys = clamp(120 + (Math.random() - 0.5) * 8, 105, 135);
    const dia = clamp(80 + (Math.random() - 0.5) * 6, 68, 92);
    const steps = Math.max(0, Math.round(1200 + (Math.random() - 0.5) * 500));
    return [
      { metric: "heart_rate", value: hr, unit: "bpm", timestamp: ts, source },
      { metric: "spo2", value: spo2, unit: "%", timestamp: ts, source },
      { metric: "bp_systolic", value: sys, unit: "mmHg", timestamp: ts, source },
      { metric: "bp_diastolic", value: dia, unit: "mmHg", timestamp: ts, source },
      { metric: "steps", value: steps, unit: "steps", timestamp: ts, source },
    ];
  }

  if (scenario === "hr_spike") {
    const p = Math.min(1, elapsedSec / 30);
    const hr = 75 + (145 - 75) * p + (Math.random() - 0.5) * 2;
    const spo2 = clamp(98 + (Math.random() - 0.5), 95, 100);
    const sys = clamp(118 + (Math.random() - 0.5) * 4, 110, 128);
    const dia = clamp(78 + (Math.random() - 0.5) * 4, 72, 85);
    return [
      { metric: "heart_rate", value: clamp(hr, 55, 190), unit: "bpm", timestamp: ts, source },
      { metric: "spo2", value: spo2, unit: "%", timestamp: ts, source },
      { metric: "bp_systolic", value: sys, unit: "mmHg", timestamp: ts, source },
      { metric: "bp_diastolic", value: dia, unit: "mmHg", timestamp: ts, source },
    ];
  }

  if (scenario === "spo2_drop") {
    const p = Math.min(1, elapsedSec / 20);
    const spo2 = 98 + (89 - 98) * p + (Math.random() - 0.5) * 0.6;
    const hr = clamp(78 + (Math.random() - 0.5) * 6, 60, 100);
    const sys = clamp(118 + (Math.random() - 0.5) * 4, 108, 128);
    const dia = clamp(78 + (Math.random() - 0.5) * 4, 70, 88);
    return [
      { metric: "heart_rate", value: hr, unit: "bpm", timestamp: ts, source },
      { metric: "spo2", value: clamp(spo2, 85, 100), unit: "%", timestamp: ts, source },
      { metric: "bp_systolic", value: sys, unit: "mmHg", timestamp: ts, source },
      { metric: "bp_diastolic", value: dia, unit: "mmHg", timestamp: ts, source },
    ];
  }

  const p = Math.min(1, elapsedSec / 30);
  const sys = 118 + (168 - 118) * p + (Math.random() - 0.5) * 2;
  const dia = 78 + (92 - 78) * p * 0.6 + (Math.random() - 0.5) * 2;
  const hr = clamp(82 + (Math.random() - 0.5) * 6, 65, 105);
  const spo2 = clamp(97 + (Math.random() - 0.5) * 1.5, 94, 99);
  return [
    { metric: "heart_rate", value: hr, unit: "bpm", timestamp: ts, source },
    { metric: "spo2", value: spo2, unit: "%", timestamp: ts, source },
    { metric: "bp_systolic", value: clamp(sys, 100, 200), unit: "mmHg", timestamp: ts, source },
    { metric: "bp_diastolic", value: clamp(dia, 60, 105), unit: "mmHg", timestamp: ts, source },
  ];
}

type LogLine = { t: string; message: string; ok?: boolean };

export function Simulator() {
  const { user } = useAuth();
  const [patientId, setPatientId] = useState(user?.role === "patient" ? user.id : "");
  const [scenario, setScenario] = useState<VitalsScenario>("normal");
  const [running, setRunning] = useState(false);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [serverBusy, setServerBusy] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startMonoRef = useRef(0);

  useEffect(() => {
    if (user?.role === "patient" && user.id) {
      setPatientId((p) => (p.trim() ? p : user.id));
    }
  }, [user?.id, user?.role]);

  const pushLog = useCallback((message: string, ok = true) => {
    const line: LogLine = { t: new Date().toISOString(), message, ok };
    setLogs((prev) => [line, ...prev].slice(0, 200));
  }, []);

  const clearTimer = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const stop = useCallback(() => {
    clearTimer();
    setRunning(false);
    pushLog("Simulation stopped.", true);
  }, [clearTimer, pushLog]);

  const sendTick = useCallback(
    async (sc: VitalsScenario, pid: string) => {
      const elapsed = (performance.now() - startMonoRef.current) / 1000;
      const readings = buildReadings(sc, elapsed);
      for (const r of readings) {
        try {
          await ingestVitalReading(pid, r);
          pushLog(`POST ingest ${r.metric}=${typeof r.value === "number" ? r.value.toFixed(1) : r.value} ${r.unit}`, true);
        } catch {
          pushLog(`Failed ingest ${r.metric}`, false);
        }
      }
    },
    [pushLog],
  );

  const start = useCallback(() => {
    const pid = patientId.trim();
    if (!pid) {
      pushLog("Enter a patient UUID.", false);
      return;
    }
    clearTimer();
    setRunning(true);
    startMonoRef.current = performance.now();
    pushLog(`Started client simulation (${scenario}) every 3s — JWT from localStorage.`, true);
    void sendTick(scenario, pid);
    intervalRef.current = setInterval(() => {
      void sendTick(scenario, pid);
    }, 3000);
  }, [patientId, scenario, sendTick, clearTimer, pushLog]);

  useEffect(
    () => () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    },
    [],
  );

  const onServerSim = async () => {
    const pid = patientId.trim();
    if (!pid) {
      pushLog("Enter a patient UUID.", false);
      return;
    }
    setServerBusy(true);
    try {
      const res = await startVitalsSimulation({ patient_id: pid, scenario, duration_seconds: 60 });
      pushLog(`Server simulate accepted: ${res.status} · ${res.duration_seconds}s · ${res.scenario}`, true);
    } catch {
      pushLog("Server simulate request failed (check auth and API URL).", false);
    } finally {
      setServerBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6 pb-8">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">IoT simulator (demo)</h1>
        <p className="mt-2 text-sm text-gray-600">
          Hidden demo page — sends wearable-style readings to <code className="text-teal-800">POST /api/vitals/ingest</code>{" "}
          using your session JWT. Not linked from the main navigation.
        </p>
      </div>

      <section className="rounded-2xl border border-amber-400/40 bg-amber-50 p-4 text-sm text-amber-950">
        Use only on staging or with consent. Alert thresholds follow backend defaults (e.g. HR warn ≥100, alert ≥130).
      </section>

      <section className="space-y-4 rounded-2xl border border-gray-100 bg-white p-4 shadow-card md:p-6">
        <div>
          <label className="text-sm font-medium text-gray-700">Patient ID (UUID)</label>
          <input
            className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3 font-mono text-sm"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          />
        </div>

        <div>
          <span className="text-sm font-medium text-gray-700">Scenario</span>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {SCENARIOS.map((s) => (
              <label
                key={s.value}
                className={`flex min-h-11 cursor-pointer flex-col rounded-xl border p-3 text-sm ${
                  scenario === s.value ? "border-teal-400 bg-teal-50 ring-1 ring-teal-200" : "border-gray-200 hover:bg-gray-50"
                }`}
              >
                <span className="flex items-center gap-2 font-semibold text-gray-900">
                  <input type="radio" name="scen" className="h-4 w-4" checked={scenario === s.value} onChange={() => setScenario(s.value)} />
                  {s.label}
                </span>
                <span className="mt-1 pl-6 text-xs text-gray-600">{s.hint}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {!running ? (
            <button
              type="button"
              className="min-h-11 rounded-xl bg-teal-400 px-5 text-sm font-semibold text-white hover:bg-teal-600"
              onClick={start}
            >
              Start simulation
            </button>
          ) : (
            <button type="button" className="min-h-11 rounded-xl bg-danger-400 px-5 text-sm font-semibold text-white hover:bg-red-600" onClick={stop}>
              Stop simulation
            </button>
          )}
        </div>

        <div className="border-t border-gray-100 pt-4">
          <p className="text-sm font-medium text-gray-800">Server-side run (60s)</p>
          <p className="mt-1 text-xs text-gray-600">
            Starts <code className="text-teal-800">POST /api/vitals/simulate</code> — same scenarios, runs in the API process so you can
            close this tab and still see updates on the dashboard.
          </p>
          <button
            type="button"
            disabled={serverBusy}
            className="mt-3 min-h-11 rounded-xl border border-gray-300 bg-white px-4 text-sm font-semibold text-gray-900 hover:bg-gray-50 disabled:opacity-50"
            onClick={() => void onServerSim()}
          >
            {serverBusy ? "Starting…" : "Start server simulation (60s)"}
          </button>
        </div>
      </section>

      <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-card">
        <h2 className="text-sm font-semibold text-gray-900">Live log</h2>
        <ul className="mt-3 max-h-80 space-y-1 overflow-y-auto font-mono text-xs">
          {logs.length === 0 ? <li className="text-gray-500">No events yet.</li> : null}
          {logs.map((l, i) => (
            <li key={`${l.t}-${i}`} className={l.ok === false ? "text-danger-400" : "text-gray-800"}>
              <span className="text-gray-400">{l.t}</span> {l.message}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
