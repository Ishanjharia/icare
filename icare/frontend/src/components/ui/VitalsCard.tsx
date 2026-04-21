import type { VitalReading } from "../../services/api";

type VitalsCardProps = {
  title: string;
  reading: VitalReading | null;
  /** Overrides numeric display (e.g. combined BP "120/80"). */
  displayValue?: string | null;
  unit?: string | null;
  liveValue?: number | null;
  liveUnit?: string | null;
  subtitle?: string;
  accent?: "default" | "amber" | "danger";
};

export function VitalsCard({
  title,
  reading,
  displayValue,
  unit: unitProp,
  liveValue,
  liveUnit,
  subtitle,
  accent = "default",
}: VitalsCardProps) {
  const hasLive = liveValue != null && !Number.isNaN(liveValue);
  const value =
    displayValue != null && displayValue !== ""
      ? displayValue
      : hasLive
        ? String(liveValue)
        : reading
          ? String(Math.round(reading.value))
          : "—";
  const unit =
    unitProp != null && unitProp !== ""
      ? unitProp
      : hasLive
        ? (liveUnit ?? reading?.unit ?? "")
        : reading?.unit ?? "";
  const border =
    accent === "danger"
      ? "border-danger-400/40 ring-1 ring-danger-400/20"
      : accent === "amber"
        ? "border-amber-400/50 ring-1 ring-amber-400/20"
        : "border-gray-100";

  return (
    <article
      className={`rounded-2xl border bg-white p-4 shadow-card ${border}`}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{title}</p>
      <p className="mt-2 text-2xl font-semibold tabular-nums text-gray-900">
        {value}
        {unit ? <span className="ml-1 text-base font-normal text-gray-500">{unit}</span> : null}
      </p>
      {subtitle ? <p className="mt-1 text-xs text-gray-500">{subtitle}</p> : null}
      {hasLive ? <p className="mt-1 text-xs font-medium text-teal-600">Live</p> : null}
    </article>
  );
}
