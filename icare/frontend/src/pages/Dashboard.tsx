import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertBanner } from "../components/ui/AlertBanner";
import { VitalsCard } from "../components/ui/VitalsCard";
import { useActivePatient } from "../hooks/useActivePatient";
import { useVitalsWebSocket } from "../hooks/useVitalsWebSocket";
import { isMedTakenToday, setMedTakenToday } from "../lib/medToday";
import {
  fetchActiveAlerts,
  fetchHealthRecords,
  fetchMedications,
  fetchVitalsSnapshot,
  type AlertOut,
  type HealthRecord,
  type Medication,
  type VitalReading,
} from "../services/api";

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function reading(r: Record<string, VitalReading> | undefined, key: string): VitalReading | null {
  if (!r) return null;
  return r[key] ?? null;
}

export function Dashboard() {
  const { patientId, isDoctor, ready } = useActivePatient();
  const enabled = ready && Boolean(patientId);
  const { latestReading, history, connectionStatus } = useVitalsWebSocket(enabled ? patientId : undefined);

  const snapshotQ = useQuery({
    queryKey: ["vitals", "snapshot", patientId],
    queryFn: () => fetchVitalsSnapshot(patientId),
    enabled,
  });

  const alertsQ = useQuery({
    queryKey: ["alerts", patientId],
    queryFn: () => fetchActiveAlerts(patientId),
    enabled,
    refetchInterval: 30_000,
  });

  const recordsQ = useQuery({
    queryKey: ["records", patientId],
    queryFn: () => fetchHealthRecords(patientId),
    enabled,
  });

  const medsQ = useQuery({
    queryKey: ["medications", patientId],
    queryFn: () => fetchMedications(patientId),
    enabled,
  });

  const readings = snapshotQ.data?.readings;
  const hrLive = latestReading?.metric === "heart_rate" ? latestReading.value : null;
  const spo2Live = latestReading?.metric === "spo2" ? latestReading.value : null;
  const sysLive = latestReading?.metric === "bp_systolic" ? latestReading.value : null;
  const diaLive = latestReading?.metric === "bp_diastolic" ? latestReading.value : null;
  const stepsLive = latestReading?.metric === "steps" ? latestReading.value : null;

  const hrR = reading(readings, "heart_rate");
  const spo2R = reading(readings, "spo2");
  const sysR = reading(readings, "bp_systolic");
  const diaR = reading(readings, "bp_diastolic");
  const stepsR = reading(readings, "steps");

  const bpDisplay =
    sysLive != null && diaLive != null
      ? `${Math.round(sysLive)}/${Math.round(diaLive)}`
      : sysR && diaR
        ? `${Math.round(sysR.value)}/${Math.round(diaR.value)}`
        : undefined;

  const hrChartData = history
    .filter((h) => h.metric === "heart_rate")
    .map((h) => ({ t: formatTime(h.timestamp), v: h.value }));

  const alerts = alertsQ.data ?? [];
  const openAlerts = alerts.filter((a) => !a.acknowledged);

  const activity = buildActivityFeed(alerts, recordsQ.data ?? []);

  if (!enabled) {
    return (
      <div className="rounded-2xl border border-amber-400/40 bg-amber-50 p-6 text-center text-sm text-amber-800">
        {isDoctor
          ? "Enter a patient UUID in the sidebar (desktop) or menu (mobile) to load this dashboard."
          : "Loading…"}
      </div>
    );
  }

  const lastWearableAt = pickLatestTimestamp(readings, latestReading);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-600">Overview of vitals, alerts, and today&apos;s care tasks.</p>
      </div>

      <AlertBanner alerts={alerts} />

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <VitalsCard
          title="Heart rate"
          reading={hrR}
          liveValue={hrLive}
          liveUnit="bpm"
          accent={openAlerts.some((a) => a.vital_type.includes("heart") || a.vital_type === "heart_rate") ? "amber" : "default"}
        />
        <VitalsCard title="SpO₂" reading={spo2R} liveValue={spo2Live} liveUnit="%" />
        <VitalsCard title="Blood pressure" reading={sysR ?? diaR} displayValue={bpDisplay} unit="mmHg" />
        <VitalsCard title="Steps" reading={stepsR} liveValue={stepsLive} liveUnit={stepsR?.unit ?? "steps"} />
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-card">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-gray-900">Heart rate (live)</h2>
            <Link to="/vitals" className="text-sm font-medium text-teal-600 hover:text-teal-800">
              Details
            </Link>
          </div>
          <div className="mt-3 h-40 w-full">
            {hrChartData.length === 0 ? (
              <p className="flex h-full items-center justify-center text-sm text-gray-500">Waiting for live readings…</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={hrChartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis dataKey="t" tick={{ fontSize: 11 }} stroke="#9CA3AF" />
                  <YAxis tick={{ fontSize: 11 }} stroke="#9CA3AF" width={32} />
                  <Tooltip />
                  <Line type="monotone" dataKey="v" stroke="#1D9E75" strokeWidth={2} dot={false} isAnimationActive={false} name="HR" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        <WearableCard connectionStatus={connectionStatus} lastAt={lastWearableAt} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-card">
          <h2 className="text-sm font-semibold text-gray-900">Recent activity</h2>
          <ul className="mt-3 max-h-64 space-y-3 overflow-y-auto text-sm">
            {activity.length === 0 ? (
              <li className="text-gray-500">No recent items.</li>
            ) : (
              activity.map((item) => (
                <li key={item.id} className="flex gap-2 border-b border-gray-50 pb-2 last:border-0">
                  <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-teal-400" aria-hidden />
                  <div>
                    <p className="font-medium text-gray-900">{item.title}</p>
                    <p className="text-xs text-gray-500">{item.sub}</p>
                  </div>
                </li>
              ))
            )}
          </ul>
        </section>

        <TodayMedications meds={medsQ.data ?? []} />
      </div>
    </div>
  );
}

function WearableCard({
  connectionStatus,
  lastAt,
}: {
  connectionStatus: string;
  lastAt: string | null;
}) {
  const tone =
    connectionStatus === "connected"
      ? "text-teal-700 bg-teal-50 border-teal-100"
      : connectionStatus === "connecting"
        ? "text-amber-700 bg-amber-50 border-amber-100"
        : "text-gray-600 bg-gray-50 border-gray-100";

  return (
    <section className={`rounded-2xl border p-4 shadow-card ${tone}`}>
      <h2 className="text-sm font-semibold">Wearable</h2>
      <p className="mt-2 text-sm capitalize">Stream: {connectionStatus}</p>
      <p className="mt-1 text-xs opacity-90">
        Last sample: {lastAt ? new Date(lastAt).toLocaleString() : "—"}
      </p>
    </section>
  );
}

function TodayMedications({ meds }: { meds: Medication[] }) {
  const active = meds.filter((m) => m.status === "active" || m.status === "Active");
  const [, bump] = useState(0);
  const force = () => bump((x) => x + 1);

  return (
    <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-card">
      <h2 className="text-sm font-semibold text-gray-900">Today&apos;s medications</h2>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <MedColumn title="Pending" items={active.filter((m) => !isMedTakenToday(m.id))} onToggle={force} />
        <MedColumn title="Taken" items={active.filter((m) => isMedTakenToday(m.id))} onToggle={force} taken />
        <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50/80 p-3 text-xs text-gray-600">
          <p className="font-semibold text-gray-800">Upcoming</p>
          <p className="mt-2">Use reminders on your phone for the next dose. Mark doses as taken when you complete them.</p>
        </div>
      </div>
    </section>
  );
}

function MedColumn({
  title,
  items,
  onToggle,
  taken,
}: {
  title: string;
  items: Medication[];
  onToggle: () => void;
  taken?: boolean;
}) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{title}</p>
      <ul className="mt-2 space-y-2">
        {items.length === 0 ? (
          <li className="text-sm text-gray-500">None</li>
        ) : (
          items.map((m) => (
            <li key={m.id} className="rounded-lg bg-teal-50/50 px-2 py-2 text-sm">
              <p className="font-medium text-gray-900">{m.name}</p>
              <p className="text-xs text-gray-600">
                {m.dosage} · {m.frequency}
              </p>
              <button
                type="button"
                className="mt-2 min-h-9 w-full rounded-lg bg-white text-xs font-semibold text-teal-800 ring-1 ring-teal-100 hover:bg-teal-50"
                onClick={() => {
                  setMedTakenToday(m.id, !taken);
                  onToggle();
                }}
              >
                {taken ? "Undo taken" : "Mark taken"}
              </button>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}

function buildActivityFeed(alerts: AlertOut[], records: HealthRecord[]) {
  const rows: { id: string; title: string; sub: string; at: number }[] = [];
  for (const a of alerts.slice(0, 12)) {
    rows.push({
      id: `a-${a.id}`,
      title: a.message || `Alert: ${a.vital_type}`,
      sub: `${formatTime(a.created_at)} · level ${a.level}`,
      at: Date.parse(a.created_at) || 0,
    });
  }
  for (const r of records.slice(0, 12)) {
    rows.push({
      id: `r-${r.id}`,
      title: `${r.record_type}: ${r.description.slice(0, 80)}${r.description.length > 80 ? "…" : ""}`,
      sub: formatTime(r.created_at),
      at: Date.parse(r.created_at) || 0,
    });
  }
  rows.sort((a, b) => b.at - a.at);
  return rows.slice(0, 12);
}

function pickLatestTimestamp(readings: Record<string, VitalReading> | undefined, latest: { timestamp?: string } | null) {
  let best: string | null = latest?.timestamp ?? null;
  if (!readings) return best;
  for (const v of Object.values(readings)) {
    if (!best || Date.parse(v.timestamp) > Date.parse(best)) best = v.timestamp;
  }
  return best;
}
