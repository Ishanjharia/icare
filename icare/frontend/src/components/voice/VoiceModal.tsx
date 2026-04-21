import type { VoiceSession } from "../../hooks/useVoice";
import { VOICE_LANGUAGES } from "./voiceLanguages";

type VoiceModalProps = {
  voice: VoiceSession;
  onDismiss: () => void;
};

export function VoiceModal({ voice, onDismiss }: VoiceModalProps) {
  if (!voice.panelOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex flex-col bg-slate-900/95 text-white backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="voice-modal-title"
    >
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <h2 id="voice-modal-title" className="text-lg font-semibold">
          Voice assistant
        </h2>
        <button
          type="button"
          className="rounded-lg bg-white/10 px-3 py-2 text-sm font-medium hover:bg-white/20"
          onClick={onDismiss}
        >
          Close
        </button>
      </div>

      <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 py-4">
        <div className="flex flex-wrap gap-2">
          <span className="w-full text-xs uppercase tracking-wide text-teal-200/90">Language</span>
          {VOICE_LANGUAGES.map((opt) => (
            <button
              key={opt.code}
              type="button"
              className={`rounded-full px-3 py-1.5 text-sm font-medium ${
                voice.speechCode === opt.code ? "bg-teal-500 text-white" : "bg-white/10 text-white/90 hover:bg-white/20"
              }`}
              onClick={() => voice.setSpeechCode(opt.code)}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="rounded-xl bg-white/5 p-4">
          <p className="text-xs uppercase tracking-wide text-teal-200/90">Examples</p>
          <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-white/90">
            {voice.examples.map((ex) => (
              <li key={ex}>{ex}</li>
            ))}
          </ul>
        </div>

        <div className="flex h-24 items-end justify-center gap-1">
          {Array.from({ length: 24 }).map((_, i) => (
            <span
              key={i}
              className="w-1.5 rounded-full bg-teal-400/80"
              style={{
                height: `${12 + ((i * 7) % 48)}px`,
                animation: "voice-bar 0.9s ease-in-out infinite",
                animationDelay: `${i * 0.04}s`,
              }}
            />
          ))}
        </div>

        <div className="grid gap-3 rounded-xl bg-black/30 p-4 text-sm">
          <div>
            <span className="text-xs text-white/50">You said</span>
            <p className="mt-1 text-base text-white">{voice.transcript || "—"}</p>
          </div>
          <div>
            <span className="text-xs text-white/50">Intent</span>
            <p className="mt-1 font-medium capitalize text-teal-200">{voice.intentLabel || "—"}</p>
          </div>
          <div>
            <span className="text-xs text-white/50">Reply (spoken in browser)</span>
            <p className="mt-1 text-white/90">{voice.responseText || "—"}</p>
          </div>
        </div>

        {voice.errorMessage ? (
          <p className="rounded-lg bg-amber-500/20 px-3 py-2 text-sm text-amber-100">{voice.errorMessage}</p>
        ) : null}

        <p className="text-center text-xs text-white/50">
          {voice.state === "listening" && "Listening… pause after you speak."}
          {voice.state === "processing" && "Processing on server…"}
          {voice.state === "speaking" && "Speaking…"}
          {voice.state === "idle" && voice.panelOpen && "Tap the mic in the bar to try again."}
        </p>
      </div>

      {voice.emergency ? (
        <div className="absolute inset-0 z-[110] flex flex-col items-center justify-center bg-red-950/95 p-6 text-center">
          <p className="text-2xl font-bold text-white">Possible emergency</p>
          <p className="mt-3 max-w-md text-sm text-red-100">
            If this is life-threatening, call <strong>102</strong> for ambulance services in India, or go to the
            nearest emergency department.
          </p>
          <a
            href="tel:102"
            className="mt-6 inline-flex min-h-[48px] min-w-[200px] items-center justify-center rounded-full bg-white px-6 text-lg font-semibold text-red-700 shadow-lg"
          >
            Call 102
          </a>
          <button type="button" className="mt-4 text-sm text-red-200 underline" onClick={voice.acknowledgeEmergency}>
            Dismiss overlay
          </button>
        </div>
      ) : null}

      <style>
        {`
          @keyframes voice-bar {
            0%, 100% { transform: scaleY(0.35); opacity: 0.5; }
            50% { transform: scaleY(1); opacity: 1; }
          }
        `}
      </style>
    </div>
  );
}
