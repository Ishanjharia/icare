import { useRef } from "react";
import type { VoiceState } from "../../hooks/useVoice";
import { useVoice } from "../../hooks/useVoice";
import { VoiceModal } from "./VoiceModal";

type VoiceButtonProps = {
  patientId: string;
};

function buttonClasses(state: VoiceState): string {
  const base =
    "flex h-14 w-14 shrink-0 items-center justify-center rounded-full shadow-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-teal-500";
  if (state === "listening") {
    return `${base} animate-pulse bg-red-500 text-white hover:bg-red-600`;
  }
  if (state === "processing") {
    return `${base} border-4 border-teal-200 bg-white text-teal-700 hover:bg-teal-50`;
  }
  if (state === "speaking") {
    return `${base} bg-blue-600 text-white hover:bg-blue-700`;
  }
  if (state === "error") {
    return `${base} bg-amber-500 text-white hover:bg-amber-600`;
  }
  return `${base} bg-teal-600 text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50`;
}

export function VoiceButton({ patientId }: VoiceButtonProps) {
  const voice = useVoice(patientId);
  const busyRef = useRef(false);

  const onClick = () => {
    if (busyRef.current) return;
    if (voice.state === "listening" || voice.state === "processing") return;
    busyRef.current = true;
    void (async () => {
      try {
        await voice.startListening();
      } finally {
        busyRef.current = false;
      }
    })();
  };

  const noPatient = !patientId.trim();

  return (
    <>
      <button
        type="button"
        className={buttonClasses(voice.state)}
        aria-label="Voice commands"
        title={noPatient ? "Set VITE_DEFAULT_PATIENT_ID in frontend .env to enable voice routing." : "Voice commands"}
        onClick={onClick}
      >
        {voice.state === "processing" ? (
          <span
            className="inline-block h-7 w-7 animate-spin rounded-full border-2 border-teal-600 border-t-transparent"
            aria-hidden
          />
        ) : voice.state === "speaking" ? (
          <span className="flex h-6 w-10 items-end justify-center gap-0.5" aria-hidden>
            {[0, 1, 2, 3].map((i) => (
              <span
                key={i}
                className="w-1 animate-pulse rounded-full bg-white"
                style={{ height: `${10 + (i % 3) * 4}px`, animationDelay: `${i * 0.12}s` }}
              />
            ))}
          </span>
        ) : (
          <svg className="h-7 w-7" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.91-3c-.49 0-.9.36-.98.85C16.52 14.2 14.47 16 12 16s-4.52-1.8-4.93-4.15c-.08-.49-.49-.85-.98-.85-.61 0-1.09.54-1 1.14.49 3 3.39 5.36 6.91 5.86V20c0 .55.45 1 1 1h2c.55 0 1-.45 1-1v-2.26c3.52-.5 6.42-2.86 6.91-5.86.1-.6-.39-1.14-1-1.14z" />
          </svg>
        )}
      </button>
      <VoiceModal voice={voice} onDismiss={voice.dismissPanel} />
    </>
  );
}
