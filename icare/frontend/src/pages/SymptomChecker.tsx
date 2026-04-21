import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { useActivePatient } from "../hooks/useActivePatient";
import { useAuth } from "../hooks/useAuth";
import { useVoice } from "../hooks/useVoice";
import {
  analyzeSymptoms,
  buildChatStreamUrl,
  fetchHealthContext,
  fetchSymptomAnalysisHistory,
  getStoredToken,
  transcribeVoiceAudio,
  type ChatTurn,
} from "../services/api";
import { VoiceModal } from "../components/voice/VoiceModal";

const TABS = ["Text", "Voice", "Context", "Chat", "History"] as const;

function pickRecorderMime(): string {
  const candidates = ["audio/webm;codecs=opus", "audio/webm"];
  for (const c of candidates) {
    if (MediaRecorder.isTypeSupported(c)) return c;
  }
  return "";
}

function SymptomVoicePanel({
  patientId,
  languageLabel,
  onApplyTranscript,
}: {
  patientId: string;
  languageLabel: string;
  onApplyTranscript: (t: string) => void;
}) {
  const voice = useVoice(patientId);

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">
        Speak clearly in <span className="font-semibold text-teal-800">{languageLabel}</span>. When finished, tap{" "}
        <span className="font-semibold">Copy transcript to text</span> to paste into the analyzer.
      </p>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="min-h-11 rounded-xl bg-teal-400 px-4 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-50"
          disabled={voice.state === "listening" || voice.state === "processing"}
          onClick={() => void voice.startListening()}
        >
          {voice.state === "listening" ? "Listening…" : voice.state === "processing" ? "Processing…" : "Start voice"}
        </button>
        <button
          type="button"
          className="min-h-11 rounded-xl border border-gray-200 px-4 text-sm font-medium text-gray-800 hover:bg-gray-50"
          onClick={() => onApplyTranscript(voice.transcript)}
        >
          Copy transcript to text
        </button>
        <button
          type="button"
          className="min-h-11 rounded-xl border border-gray-200 px-4 text-sm font-medium text-gray-800 hover:bg-gray-50"
          onClick={voice.dismissPanel}
        >
          Reset session
        </button>
      </div>
      <div className="rounded-xl border border-gray-100 bg-teal-50/40 p-3 text-sm text-gray-800">
        <p className="text-xs font-semibold uppercase text-teal-800">Transcript</p>
        <p className="mt-1 whitespace-pre-wrap">{voice.transcript || "—"}</p>
      </div>
      <VoiceModal voice={voice} onDismiss={voice.dismissPanel} />
    </div>
  );
}

export function SymptomChecker() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const { patientId, isDoctor, ready } = useActivePatient();
  const enabled = ready && Boolean(patientId);
  const [tab, setTab] = useState(0);
  const [text, setText] = useState("");
  const [lang, setLang] = useState(user?.language ?? "English");
  const [includeVitals, setIncludeVitals] = useState(true);
  const [recBusy, setRecBusy] = useState(false);
  const [recErr, setRecErr] = useState<string | null>(null);

  const [chatMessage, setChatMessage] = useState("");
  const [chatReply, setChatReply] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const chatTurnsRef = useRef<ChatTurn[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  const contextQ = useQuery({
    queryKey: ["health-context", patientId],
    queryFn: () => fetchHealthContext(patientId),
    enabled: enabled && tab === 2,
  });

  const historyQ = useQuery({
    queryKey: ["symptom-history", patientId],
    queryFn: () => fetchSymptomAnalysisHistory(patientId),
    enabled: enabled && tab === 4,
  });

  const analyzeMut = useMutation({
    mutationFn: () =>
      analyzeSymptoms({
        symptoms_text: text.trim(),
        language: lang,
        include_vitals: includeVitals,
        patient_id: isDoctor ? patientId : null,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["symptom-history", patientId] });
    },
  });

  const result = analyzeMut.data;

  const onApplyTranscript = useCallback((t: string) => {
    setText((prev) => (prev.trim() ? `${prev.trim()}\n${t}` : t));
  }, []);

  const recordBlob = async (): Promise<Blob | null> => {
    setRecErr(null);
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mime = pickRecorderMime();
    const rec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
    const chunks: Blob[] = [];
    rec.ondataavailable = (e) => {
      if (e.data.size) chunks.push(e.data);
    };
    const done = new Promise<Blob>((resolve, reject) => {
      rec.onstop = () => {
        stream.getTracks().forEach((tr) => tr.stop());
        resolve(new Blob(chunks, { type: mime || "audio/webm" }));
      };
      rec.onerror = () => reject(new Error("Recorder error"));
    });
    rec.start();
    await new Promise((r) => setTimeout(r, 3500));
    rec.stop();
    return done;
  };

  const onQuickRecord = async () => {
    if (!enabled) return;
    setRecBusy(true);
    try {
      const blob = await recordBlob();
      if (!blob) return;
      const out = await transcribeVoiceAudio(blob);
      if (out.success && out.transcription) {
        setText((p) => (p.trim() ? `${p.trim()}\n${out.transcription}` : out.transcription));
      } else {
        setRecErr(out.error ?? "Transcription failed");
      }
    } catch {
      setRecErr("Could not access microphone or transcribe.");
    } finally {
      setRecBusy(false);
    }
  };

  const readAloud = () => {
    if (!result?.symptoms_summary && !result?.recommendations?.length) return;
    window.speechSynthesis.cancel();
    const body = [result.symptoms_summary, ...(result.recommendations ?? [])].join(". ");
    const u = new SpeechSynthesisUtterance(body);
    u.lang = "en-US";
    window.speechSynthesis.speak(u);
  };

  useEffect(
    () => () => {
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
    },
    [],
  );

  const sendChatStream = useCallback(() => {
    const token = getStoredToken();
    const msg = chatMessage.trim();
    if (!token || !msg || !enabled) return;

    eventSourceRef.current?.close();
    setChatBusy(true);
    setChatReply("");

    const prior = chatTurnsRef.current;
    const url = buildChatStreamUrl({
      token,
      message: msg,
      language: lang,
      patientId: isDoctor ? patientId : undefined,
      history: prior,
    });

    let assembled = "";
    const source = new EventSource(url);
    eventSourceRef.current = source;

    source.onmessage = (ev) => {
      const d = ev.data;
      try {
        const parsed = JSON.parse(d);
        if (parsed === "[DONE]") {
          source.close();
          eventSourceRef.current = null;
          chatTurnsRef.current = [...prior, { role: "user", content: msg }, { role: "assistant", content: assembled }];
          setChatBusy(false);
          setChatMessage("");
          return;
        }
        if (typeof parsed === "string") {
          assembled += parsed;
          setChatReply(assembled);
        }
      } catch {
        if (d === "[DONE]" || d === '"[DONE]"') {
          source.close();
          eventSourceRef.current = null;
          chatTurnsRef.current = [...prior, { role: "user", content: msg }, { role: "assistant", content: assembled }];
          setChatBusy(false);
          setChatMessage("");
          return;
        }
        assembled += d;
        setChatReply(assembled);
      }
    };

    source.onerror = () => {
      source.close();
      eventSourceRef.current = null;
      setChatBusy(false);
    };
  }, [chatMessage, enabled, isDoctor, lang, patientId]);

  if (!enabled) {
    return (
      <div className="rounded-2xl border border-amber-400/40 bg-amber-50 p-6 text-center text-sm text-amber-800">
        Select a patient UUID (doctor) to run symptom analysis.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Symptom checker</h1>
        <p className="mt-1 text-sm text-gray-600">Describe how you feel. This tool does not replace a clinician.</p>
      </div>

      <div className="flex flex-wrap gap-1 rounded-xl bg-gray-100 p-1">
        {TABS.map((label, i) => (
          <button
            key={label}
            type="button"
            className={`min-h-11 min-w-[72px] flex-1 rounded-lg text-sm font-semibold ${
              tab === i ? "bg-white text-teal-800 shadow-sm" : "text-gray-600 hover:text-gray-900"
            }`}
            onClick={() => setTab(i)}
          >
            {label}
          </button>
        ))}
      </div>

      <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-card md:p-6">
        {tab === 0 ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <label htmlFor="symptom-lang" className="text-sm font-medium text-gray-700">
                Response language
              </label>
              <select
                id="symptom-lang"
                className="min-h-11 rounded-lg border border-gray-200 px-3 text-sm"
                value={lang}
                onChange={(e) => setLang(e.target.value)}
              >
                {["English", "Hindi", "Marathi", "Tamil", "Telugu", "Bengali", "Gujarati", "Kannada", "Malayalam", "Punjabi"].map(
                  (l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ),
                )}
              </select>
              <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800 ring-1 ring-teal-100">
                {lang}
              </span>
            </div>
            <label className="flex min-h-11 cursor-pointer items-center gap-2 text-sm text-gray-800">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300 text-teal-600"
                checked={includeVitals}
                onChange={(e) => setIncludeVitals(e.target.checked)}
              />
              Include latest vitals snapshot in analysis (server)
            </label>
            <label htmlFor="symptoms" className="text-sm font-medium text-gray-700">
              Symptoms
            </label>
            <textarea
              id="symptoms"
              className="min-h-32 w-full rounded-xl border border-gray-200 p-3 text-base outline-none ring-teal-400 focus:ring-2"
              placeholder="e.g. fever and sore throat for two days…"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </div>
        ) : null}

        {tab === 1 ? (
          <div className="space-y-4">
            <SymptomVoicePanel patientId={patientId} languageLabel={lang} onApplyTranscript={onApplyTranscript} />
            <div className="border-t border-gray-100 pt-4">
              <p className="text-sm font-medium text-gray-800">Quick 3s recording (REST transcribe)</p>
              <button
                type="button"
                className="mt-2 min-h-11 rounded-xl bg-gray-900 px-4 text-sm font-semibold text-white hover:bg-gray-800 disabled:opacity-50"
                disabled={recBusy}
                onClick={() => void onQuickRecord()}
              >
                {recBusy ? "Recording…" : "Record 3 seconds"}
              </button>
              {recErr ? <p className="mt-2 text-sm text-danger-400">{recErr}</p> : null}
            </div>
          </div>
        ) : null}

        {tab === 2 ? (
          <div>
            <p className="text-sm text-gray-600">
              Latest vitals and record context is <span className="font-semibold text-teal-800">auto-attached</span> on
              analyze (server-side). Preview:
            </p>
            <pre className="mt-3 max-h-64 overflow-auto rounded-xl bg-gray-50 p-3 text-xs text-gray-800">
              {contextQ.isLoading ? "Loading…" : JSON.stringify(contextQ.data ?? {}, null, 2)}
            </pre>
          </div>
        ) : null}

        {tab === 3 ? (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">
              Streams via <code className="text-teal-800">EventSource</code> to{" "}
              <code className="break-all text-teal-800">/api/chat/stream?token=…</code> (JWT in query for browser
              limitation). Replies append in real time.
            </p>
            <textarea
              className="min-h-24 w-full rounded-xl border border-gray-200 p-3 text-base outline-none ring-teal-400 focus:ring-2"
              placeholder="Ask a health question…"
              value={chatMessage}
              onChange={(e) => setChatMessage(e.target.value)}
              disabled={chatBusy}
            />
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="min-h-11 rounded-xl bg-teal-400 px-5 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-50"
                disabled={!chatMessage.trim() || chatBusy}
                onClick={sendChatStream}
              >
                {chatBusy ? "Streaming…" : "Send (stream)"}
              </button>
              <button
                type="button"
                className="min-h-11 rounded-xl border border-gray-200 px-4 text-sm font-medium text-gray-800 hover:bg-gray-50"
                disabled={chatBusy}
                onClick={() => {
                  chatTurnsRef.current = [];
                  setChatReply("");
                  setChatMessage("");
                }}
              >
                Clear chat
              </button>
            </div>
            <div className="rounded-xl border border-gray-100 bg-teal-50/40 p-3">
              <p className="text-xs font-semibold uppercase text-teal-800">Assistant</p>
              <p className="mt-2 whitespace-pre-wrap text-sm text-gray-900">{chatReply || (chatBusy ? "…" : "—")}</p>
            </div>
          </div>
        ) : null}

        {tab === 4 ? (
          <div>
            <p className="text-sm text-gray-600">Saved symptom analyses (from POST /api/symptoms/analyze).</p>
            {historyQ.isLoading ? <p className="mt-2 text-sm text-gray-500">Loading…</p> : null}
            <ul className="mt-3 max-h-80 space-y-2 overflow-y-auto text-sm">
              {(historyQ.data ?? []).length === 0 ? (
                <li className="text-gray-500">No history yet.</li>
              ) : (
                (historyQ.data ?? []).map((h) => (
                  <li key={h.id} className="rounded-lg border border-gray-100 bg-gray-50/80 p-3">
                    <p className="text-xs text-gray-500">{new Date(h.created_at).toLocaleString()}</p>
                    <p className="mt-1 font-medium text-gray-900">{h.description.slice(0, 160)}{h.description.length > 160 ? "…" : ""}</p>
                    <p className="mt-1 text-xs text-teal-800">
                      Severity: {(h.report_data?.severity_level as string) ?? "—"}
                    </p>
                  </li>
                ))
              )}
            </ul>
          </div>
        ) : null}

        {tab <= 2 ? (
          <div className="mt-6 flex flex-wrap gap-2">
            <button
              type="button"
              className="min-h-11 rounded-xl bg-teal-400 px-5 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-50"
              disabled={!text.trim() || analyzeMut.isPending}
              onClick={() => analyzeMut.mutate()}
            >
              {analyzeMut.isPending ? "Analyzing…" : "Analyze"}
            </button>
            {result ? (
              <button
                type="button"
                className="min-h-11 rounded-xl border border-gray-200 px-4 text-sm font-medium text-gray-800 hover:bg-gray-50"
                onClick={readAloud}
              >
                Read aloud
              </button>
            ) : null}
          </div>
        ) : null}
      </section>

      {result ? (
        <section className="space-y-4 rounded-2xl border border-gray-100 bg-white p-4 shadow-card md:p-6">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full px-3 py-1 text-xs font-bold uppercase ${
                result.urgent_care_needed ? "bg-danger-50 text-danger-400" : "bg-teal-50 text-teal-800"
              }`}
            >
              {result.severity_level}
            </span>
            {result.urgent_care_needed ? (
              <span className="text-sm font-semibold text-danger-400">Urgent care suggested</span>
            ) : null}
          </div>
          <p className="text-sm text-gray-800">{result.symptoms_summary}</p>
          <div>
            <p className="text-xs font-semibold uppercase text-gray-500">Possible conditions</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {(result.possible_conditions ?? []).map((c) => (
                <span key={c} className="rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-800 ring-1 ring-teal-100">
                  {c}
                </span>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-gray-500">Recommendations</p>
            <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-gray-800">
              {(result.recommendations ?? []).map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>
          {result.follow_up_questions?.length ? (
            <div>
              <p className="text-xs font-semibold uppercase text-gray-500">Follow-up questions</p>
              <ul className="mt-2 list-inside list-decimal space-y-1 text-sm text-gray-700">
                {result.follow_up_questions.map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}

      {analyzeMut.isError ? (
        <p className="text-sm text-danger-400">Analysis failed. Check your connection and try again.</p>
      ) : null}

      <footer className="rounded-2xl border border-amber-400/40 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-semibold">Medical disclaimer</p>
        <p className="mt-2 leading-relaxed">
          {result?.medical_disclaimer ??
            "I-CARE symptom analysis is informational only and is not a diagnosis. Always follow advice from a licensed clinician and seek emergency services when needed."}
        </p>
      </footer>
    </div>
  );
}
