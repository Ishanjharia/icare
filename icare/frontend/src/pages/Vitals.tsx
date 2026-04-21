import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { VitalsCard } from "../components/ui/VitalsCard";
import { useActivePatient } from "../hooks/useActivePatient";
import { useVitalsWebSocket } from "../hooks/useVitalsWebSocket";
import {
  fetchThresholds,
  fetchVitalsHistory,
  fetchVitalsSnapshot,
  type MetricThresholds,
  type ThresholdConfig,
  type VitalReading,
} from "../services/api";

type MetricKey = "heart_rate" | "spo2" | "bp_systolic" | "bp_diastolic";
type RangeKey = "live" | "1" | "6" | "24";

const METRICS: { key: MetricKey; label: string }[] = [
  { key: "heart_rate", label: "HR" },
  { key: "spo2", label: "SpO₂" },
  { key: "bp_systolic", label: "BP systolic" },
  { key: "bp_diastolic", label: "BP diastolic" },
];

const RANGES: { key: RangeKey; label: string; hours: number }[] = [
  { key: "live", label: "Live", hours: 0 },
  { key: "1", label: "1 hr", hours: 1 },
  { key: "6", label: "6 hr", hours: 6 },
  { key: "24", label: "24 hr", hours: 24 },
];

function formatTick(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function reading(map: Record<string, VitalReading> | undefined, key: string): VitalReading | null {
  if (!map) return null;
  return map[key] ?? null;
}

function thresholdForMetric(cfg: ThresholdConfig | undefined, metric: MetricKey): MetricThresholds | null {
  const m = cfg?.[metric];
  return m ?? null;
}

export function Vitals() {
  const { patientId, ready } = useActivePatient();
  const enabled = ready && Boolean(patientId);
  const [metric, setMetric] = useState<MetricKey>("heart_rate");
  const [range, setRange] = useState<RangeKey>("live");

  const hours = RANGES.find((r) => r.key === range)?.hours ?? 1;
  const { latestReading, history, connectionStatus } = useVitalsWebSocket(enabled ? patientId : undefined);

  const snapshotQ = useQuery({
    queryKey: ["vitals", "snapshot", patientId],
    queryFn: () => fetchVitalsSnapshot(patientId),
    enabled,
    refetchInterval: 30_000,
  });

  const thresholdsQ = useQuery({
    queryKey: ["vitals", "thresholds", patientId],
    queryFn: () => fetchThresholds(patientId),
    enabled,
  });

  const historyQ = useQuery({
    queryKey: ["vitals", "history", patientId, metric, hours],
    queryFn: () => fetchVitalsHistory(patientId, metric, hours),
    enabled: enabled && hours > 0,
  });

  const readings = snapshotQ.data?.readings;
  const thr = thresholdsQ.data;

  const chartPoints = useMemo(() => {
    if (hours === 0) {
      return history
        .filter((h) => h.metric === metric)
        .map((h) => ({ t: h.timestamp, label: formatTick(h.timestamp), v: h.value }));
    }
    const pts = historyQ.data ?? [];
    return pts.map((h) => ({ t: h.timestamp, label: formatTick(h.timestamp), v: h.value }));
  }, [hours, history, historyQ.data, metric]);

  const tcfg = thresholdForMetric(thr, metric);

  if (!enabled) {
    return (
      <div className="rounded-2xl border border-amber-400/40 bg-amber-50 p-6 text-center text-sm text-amber-800">
        Select a patient (doctor) or sign in as a patient to view vitals.
      </div>
    );
  }

  const hr = reading(readings, "heart_rate");
  const spo2 = reading(readings, "spo2");
  const sys = reading(readings, "bp_systolic");
  const dia = reading(readings, "bp_diastolic");
  const steps = reading(readings, "steps");

  const liveHr = latestReading?.metric === "heart_rate" ? latestReading.value : null;
  const liveSpo2 = latestReading?.metric === "spo2" ? latestReading.value : null;
  const liveSys = latestReading?.metric === "bp_systolic" ? latestReading.value : null;
  const liveDia = latestReading?.metric === "bp_diastolic" ? latestReading.value : null;
  const liveSteps = latestReading?.metric === "steps" ? latestReading.value : null;

  const bpDisplay =
    liveSys != null && liveDia != null
      ? `${Math.round(liveSys)}/${Math.round(liveDia)}`
      : sys && dia
        ? `${Math.round(sys.value)}/${Math.round(dia.value)}`
        : undefined;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Vitals</h1>
          <p className="mt-1 text-sm text-gray-600 capitalize">Live stream: {connectionStatus}</p>
        </div>
      </div>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <VitalsCard title="Heart rate" reading={hr} liveValue={liveHr} liveUnit="bpm" />
        <VitalsCard title="SpO₂" reading={spo2} liveValue={liveSpo2} liveUnit="%" />
        <VitalsCard title="Blood pressure" reading={sys ?? dia} displayValue={bpDisplay} unit="mmHg" />
        <VitalsCard title="Steps" reading={steps} liveValue={liveSteps} liveUnit={steps?.unit ?? "steps"} />
      </section>

      <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-card">
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Metric</span>
            {METRICS.map((m) => (
              <button
                key={m.key}
                type="button"
                onClick={() => setMetric(m.key)}
                className={`min-h-11 rounded-xl px-3 text-sm font-semibold ${
                  metric === m.key ? "bg-teal-400 text-white" : "bg-gray-100 text-gray-800 hover:bg-gray-200"
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Range</span>
            {RANGES.map((r) => (
              <button
                key={r.key}
                type="button"
                onClick={() => setRange(r.key)}
                className={`min-h-11 rounded-xl px-3 text-sm font-semibold ${
                  range === r.key ? "bg-teal-50 text-teal-800 ring-2 ring-teal-400" : "bg-gray-100 text-gray-800 hover:bg-gray-200"
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-6 h-72 w-full">
          {chartPoints.length === 0 ? (
            <p className="flex h-full items-center justify-center text-sm text-gray-500">No samples in this window.</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartPoints} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} stroke="#9CA3AF" minTickGap={24} />
                <YAxis tick={{ fontSize: 11 }} stroke="#9CA3AF" width={40} domain={["auto", "auto"]} />
                <Tooltip />
                <Legend />
                {tcfg?.alert_high != null ? (
                  <ReferenceLine
                    y={tcfg.alert_high}
                    stroke="#E24B4A"
                    strokeDasharray="4 4"
                    label={{ value: "Alert high", fill: "#E24B4A", fontSize: 10 }}
                  />
                ) : null}
                {tcfg?.critical_high != null ? (
                  <ReferenceLine y={tcfg.critical_high} stroke="#E24B4A" strokeDasharray="2 6" strokeOpacity={0.5} />
                ) : null}
                {tcfg?.warn_high != null ? (
                  <ReferenceLine
                    y={tcfg.warn_high}
                    stroke="#EF9F27"
                    strokeDasharray="4 4"
                    label={{ value: "Warn high", fill: "#BA7517", fontSize: 10 }}
                  />
                ) : null}
                {tcfg?.alert_low != null ? (
                  <ReferenceLine
                    y={tcfg.alert_low}
                    stroke="#E24B4A"
                    strokeDasharray="4 4"
                    label={{ value: "Alert low", fill: "#E24B4A", fontSize: 10 }}
                  />
                ) : null}
                {tcfg?.warn_low != null ? (
                  <ReferenceLine y={tcfg.warn_low} stroke="#EF9F27" strokeDasharray="4 4" />
                ) : null}
                {tcfg?.critical_low != null ? (
                  <ReferenceLine y={tcfg.critical_low} stroke="#E24B4A" strokeDasharray="2 6" strokeOpacity={0.5} />
                ) : null}
                <Line
                  type="monotone"
                  dataKey="v"
                  name={METRICS.find((m) => m.key === metric)?.label ?? metric}
                  stroke="#1D9E75"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>
    </div>
  );
}
