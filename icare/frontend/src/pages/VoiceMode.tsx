import { useVoice } from "../hooks/useVoice";
import { useActivePatient } from "../hooks/useActivePatient";
import { VOICE_EXAMPLES, VOICE_LANGUAGES, type VoiceSpeechCode } from "../components/voice/voiceLanguages";
import { VoiceModal } from "../components/voice/VoiceModal";

export function VoiceMode() {
  const { patientId, ready } = useActivePatient();
  const voice = useVoice(patientId);
  const enabled = ready && Boolean(patientId);

  if (!enabled) {
    return (
      <div className="rounded-2xl border border-amber-400/40 bg-amber-50 p-6 text-center text-sm text-amber-800">
        Select a patient UUID (doctor) or sign in as a patient to use voice mode.
      </div>
    );
  }

  const listening = voice.state === "listening";
  const processing = voice.state === "processing";

  return (
    <div className="mx-auto max-w-xl space-y-8 pb-8">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-gray-900">Voice mode</h1>
        <p className="mt-1 text-sm text-gray-600">Hands-free commands and spoken responses.</p>
      </div>

      <div className="flex flex-col items-center gap-6">
        <div className="relative flex items-center justify-center">
          {(listening || processing) && (
            <span
              className={`absolute inline-flex h-52 w-52 rounded-full opacity-40 ${
                listening ? "animate-ping bg-teal-400" : "bg-amber-400"
              }`}
              aria-hidden
            />
          )}
          <button
            type="button"
            onClick={() => void voice.startListening()}
            disabled={listening || processing}
            className="relative flex h-44 w-44 items-center justify-center rounded-full bg-gradient-to-br from-teal-400 to-teal-600 text-white shadow-xl ring-4 ring-teal-50 hover:from-teal-500 hover:to-teal-700 disabled:cursor-not-allowed disabled:opacity-80"
            aria-label="Start listening"
          >
            <svg className="h-16 w-16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.91-3c-.49 0-.9.36-.98.85C16.52 14.2 14.47 16 12 16s-4.52-1.8-4.93-4.15c-.08-.49-.49-.85-.98-.85-.61 0-1.09.54-1 1.14.49 3 3.39 5.36 6.91 5.86V20c0 .55.45 1 1 1h2c.55 0 1-.45 1-1v-2.26c3.52-.5 6.42-2.86 6.91-5.86.1-.6-.39-1.14-1-1.14z" />
            </svg>
          </button>
        </div>

        {listening ? (
          <div className="flex h-10 w-full max-w-xs items-end justify-center gap-1" aria-hidden>
            {Array.from({ length: 16 }).map((_, i) => (
              <span
                key={i}
                className="w-1.5 rounded-full bg-teal-400"
                style={{
                  height: `${12 + ((i * 7) % 28)}px`,
                  animation: "vm-pulse 0.8s ease-in-out infinite",
                  animationDelay: `${i * 0.05}s`,
                }}
              />
            ))}
          </div>
        ) : null}

        <style>{`@keyframes vm-pulse { 0%,100%{transform:scaleY(0.5);opacity:.5} 50%{transform:scaleY(1);opacity:1} }`}</style>

        <div className="w-full rounded-2xl border border-gray-100 bg-white p-4 shadow-card">
          <p className="text-xs font-semibold uppercase text-gray-500">Language</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {VOICE_LANGUAGES.map((l) => (
              <button
                key={l.code}
                type="button"
                onClick={() => voice.setSpeechCode(l.code as VoiceSpeechCode)}
                className={`min-h-11 rounded-xl px-3 text-xs font-semibold ${
                  voice.speechCode === l.code ? "bg-teal-400 text-white" : "bg-gray-100 text-gray-800 hover:bg-gray-200"
                }`}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>

        <div className="w-full space-y-3 rounded-2xl border border-gray-100 bg-white p-4 text-left shadow-card">
          <p className="text-xs font-semibold uppercase text-gray-500">Transcript</p>
          <p className="min-h-[3rem] text-sm text-gray-900">{voice.transcript || "—"}</p>
          <p className="text-xs font-semibold uppercase text-gray-500">Response</p>
          <p className="text-sm text-gray-800">{voice.responseText || "—"}</p>
          {voice.intentLabel ? (
            <p className="text-xs text-teal-700">
              Intent: <span className="font-medium">{voice.intentLabel}</span>
            </p>
          ) : null}
          {voice.errorMessage ? <p className="text-sm text-danger-400">{voice.errorMessage}</p> : null}
        </div>

        <div className="w-full overflow-x-auto rounded-2xl border border-gray-100 bg-white shadow-card">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-teal-50/80 text-xs uppercase text-teal-900">
              <tr>
                <th className="px-4 py-3">Example commands</th>
              </tr>
            </thead>
            <tbody>
              {VOICE_EXAMPLES[voice.speechCode].map((ex, i) => (
                <tr key={i} className="border-t border-gray-100">
                  <td className="px-4 py-3 text-gray-800">{ex}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <VoiceModal voice={voice} onDismiss={voice.dismissPanel} />
    </div>
  );
}
