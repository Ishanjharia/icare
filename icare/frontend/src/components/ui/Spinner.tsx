export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-teal-800" role="status" aria-live="polite">
      <span
        className="inline-block h-10 w-10 animate-spin rounded-full border-[3px] border-teal-100 border-t-teal-400"
        aria-hidden
      />
      <span className="text-sm text-gray-600">{label}</span>
    </div>
  );
}
