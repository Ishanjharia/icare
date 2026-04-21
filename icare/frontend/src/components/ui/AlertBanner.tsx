import { Link } from "react-router-dom";
import type { AlertOut } from "../../services/api";

export function AlertBanner({ alerts }: { alerts: AlertOut[] }) {
  const open = alerts.filter((a) => !a.acknowledged);
  if (open.length === 0) return null;

  const worst = Math.max(...open.map((a) => a.level));
  const isCritical = worst >= 5;
  const bg = isCritical ? "bg-danger-50 border-danger-400/40" : "bg-amber-50 border-amber-400/50";
  const text = isCritical ? "text-danger-400" : "text-amber-600";

  return (
    <div className={`mb-4 rounded-xl border px-4 py-3 shadow-card ${bg}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className={`text-sm font-semibold ${text}`}>
          {open.length} active alert{open.length > 1 ? "s" : ""}
          {isCritical ? " — critical" : ""}
        </p>
        <Link
          to="/alerts"
          className="inline-flex min-h-11 min-w-[44px] items-center justify-center rounded-lg bg-white px-3 text-sm font-medium text-teal-800 shadow-sm ring-1 ring-gray-200"
        >
          View alerts
        </Link>
      </div>
    </div>
  );
}
