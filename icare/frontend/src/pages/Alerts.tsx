import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useActivePatient } from "../hooks/useActivePatient";
import { acknowledgeAlert, fetchActiveAlerts, fetchAlertPipeline, type AlertOut } from "../services/api";

function levelStyle(level: number): string {
  if (level >= 5) return "border-danger-400/50 bg-danger-50";
  if (level >= 3) return "border-amber-400/50 bg-amber-50";
  return "border-gray-200 bg-white";
}

export function Alerts() {
  const qc = useQueryClient();
  const { patientId, ready } = useActivePatient();
  const enabled = ready && Boolean(patientId);

  const alertsQ = useQuery({
    queryKey: ["alerts", patientId],
    queryFn: () => fetchActiveAlerts(patientId),
    enabled,
    refetchInterval: 15_000,
  });

  const pipeQ = useQuery({
    queryKey: ["alerts", "pipeline", patientId],
    queryFn: () => fetchAlertPipeline(patientId),
    enabled,
    refetchInterval: 20_000,
  });

  const ackMut = useMutation({
    mutationFn: (id: string) => acknowledgeAlert(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["alerts", patientId] });
      void qc.invalidateQueries({ queryKey: ["alerts", "pipeline", patientId] });
    },
  });

  if (!enabled) {
    return (
      <div className="rounded-2xl border border-amber-400/40 bg-amber-50 p-6 text-center text-sm text-amber-800">
        Select a patient to view alerts.
      </div>
    );
  }

  const alerts = (alertsQ.data ?? []).filter((a) => !a.acknowledged);
  const pipe = pipeQ.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Alerts</h1>
        <p className="mt-1 text-sm text-gray-600">Acknowledge alerts when you have reviewed them.</p>
      </div>

      {alerts.some((a) => a.level >= 5) ? (
        <a
          href="tel:102"
          className="flex min-h-12 items-center justify-center rounded-xl bg-danger-400 px-4 text-center text-sm font-bold text-white shadow-md hover:bg-red-600"
        >
          Call 102 — critical alert
        </a>
      ) : null}

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-900">Active</h2>
        {alertsQ.isLoading ? <p className="text-sm text-gray-500">Loading…</p> : null}
        {alerts.length === 0 && !alertsQ.isLoading ? (
          <p className="rounded-xl border border-gray-100 bg-white p-6 text-center text-sm text-gray-600 shadow-card">
            No active alerts.
          </p>
        ) : (
          alerts.map((a) => <AlertCard key={a.id} alert={a} onAck={() => ackMut.mutate(a.id)} busy={ackMut.isPending} />)
        )}
      </section>

      <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-card">
        <h2 className="text-sm font-semibold text-gray-900">Pipeline status</h2>
        <p className="mt-1 text-xs text-gray-500">Escalation path for this patient (from backend).</p>
        {pipeQ.isLoading ? <p className="mt-3 text-sm text-gray-500">Loading…</p> : null}
        {pipe ? (
          <ul className="mt-4 space-y-2 text-sm">
            {pipe.steps.map((s, i) => (
              <li key={i} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-gray-50 px-3 py-2">
                <span className="font-medium text-gray-800">
                  Level {s.from_level} → {s.to_level}
                </span>
                <span className="text-xs text-gray-600">
                  after {s.delay_seconds}s · {s.action}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
        {pipe?.active_alerts?.length ? (
          <p className="mt-3 text-xs text-gray-600">Pipeline also tracks {pipe.active_alerts.length} active alert(s).</p>
        ) : null}
      </section>
    </div>
  );
}

function AlertCard({ alert, onAck, busy }: { alert: AlertOut; onAck: () => void; busy: boolean }) {
  const border = levelStyle(alert.level);
  return (
    <article className={`rounded-2xl border p-4 shadow-card ${border}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{alert.vital_type}</p>
          <p className="mt-1 text-lg font-semibold tabular-nums text-gray-900">
            {alert.value}
            <span className="ml-1 text-sm font-normal text-gray-600">vs threshold {alert.threshold}</span>
          </p>
          <p className="mt-2 text-sm text-gray-800">{alert.message}</p>
          <p className="mt-1 text-xs text-gray-500">{new Date(alert.created_at).toLocaleString()}</p>
        </div>
        <button
          type="button"
          className="min-h-11 shrink-0 rounded-xl bg-teal-400 px-4 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-50"
          disabled={busy}
          onClick={onAck}
        >
          Acknowledge
        </button>
      </div>
    </article>
  );
}
