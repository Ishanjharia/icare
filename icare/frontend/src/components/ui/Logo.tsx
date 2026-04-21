export function Logo({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-400 text-lg font-bold text-white shadow-card"
        aria-hidden
      >
        I
      </span>
      <span className="text-lg font-semibold tracking-tight text-teal-800">I-CARE</span>
    </div>
  );
}
