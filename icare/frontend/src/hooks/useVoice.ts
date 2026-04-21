import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { VoiceSpeechCode } from "../components/voice/voiceLanguages";
import { VOICE_LANGUAGES, VOICE_EXAMPLES } from "../components/voice/voiceLanguages";

export type VoiceState = "idle" | "listening" | "processing" | "speaking" | "error";

export type VoiceSession = {
  state: VoiceState;
  panelOpen: boolean;
  transcript: string;
  responseText: string;
  intentLabel: string;
  emergency: boolean;
  errorMessage: string | null;
  speechCode: VoiceSpeechCode;
  setSpeechCode: (code: VoiceSpeechCode) => void;
  examples: string[];
  startListening: () => Promise<void>;
  dismissPanel: () => void;
  acknowledgeEmergency: () => void;
};

type IntentWsPayload = {
  type: "intent";
  intent?: string;
  confidence?: number;
  response_text?: string;
  action?: string;
  action_params?: { path?: string };
};

function pickRecorderMime(): string {
  const candidates = ["audio/webm;codecs=opus", "audio/webm"];
  for (const c of candidates) {
    if (MediaRecorder.isTypeSupported(c)) return c;
  }
  return "";
}

function createSilenceDetector(
  stream: MediaStream,
  onSilence: () => void,
  opts: { minMsBeforeArm: number; silenceMs: number; threshold: number },
): () => void {
  const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioContextClass) {
    return () => {};
  }
  const ctx = new AudioContextClass();
  const source = ctx.createMediaStreamSource(stream);
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 512;
  analyser.smoothingTimeConstant = 0.85;
  source.connect(analyser);
  const data = new Uint8Array(analyser.frequencyBinCount);
  const started = performance.now();
  let lastSound = performance.now();
  let armed = false;
  let stopped = false;

  const tick = () => {
    if (stopped) return;
    const now = performance.now();
    if (!armed && now - started >= opts.minMsBeforeArm) {
      armed = true;
    }
    analyser.getByteFrequencyData(data);
    let sum = 0;
    for (let i = 0; i < data.length; i += 1) sum += data[i];
    const avg = sum / data.length;
    if (avg > opts.threshold) {
      lastSound = now;
    }
    if (armed && now - lastSound >= opts.silenceMs) {
      stopped = true;
      void ctx.close().catch(() => {});
      onSilence();
      return;
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  return () => {
    stopped = true;
    void ctx.close().catch(() => {});
  };
}

export function useVoice(patientId: string): VoiceSession {
  const navigate = useNavigate();
  const [state, setState] = useState<VoiceState>("idle");
  const [panelOpen, setPanelOpen] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [responseText, setResponseText] = useState("");
  const [intentLabel, setIntentLabel] = useState("");
  const [emergency, setEmergency] = useState(false);
  const [speechCode, setSpeechCode] = useState<VoiceSpeechCode>("hi-IN");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const stopSilenceRef = useRef<(() => void) | null>(null);
  const speechCodeRef = useRef<VoiceSpeechCode>(speechCode);
  speechCodeRef.current = speechCode;

  const backendLanguage = VOICE_LANGUAGES.find((x) => x.code === speechCode)?.backendLanguage ?? "English";

  const cleanupStream = useCallback(() => {
    stopSilenceRef.current?.();
    stopSilenceRef.current = null;
    const rec = recorderRef.current;
    recorderRef.current = null;
    if (rec && rec.state === "recording") {
      rec.stop();
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const closeWs = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }
    wsRef.current = null;
  }, []);

  const acknowledgeEmergency = useCallback(() => {
    setEmergency(false);
  }, []);

  const dismissPanel = useCallback(() => {
    window.speechSynthesis.cancel();
    cleanupStream();
    closeWs();
    setPanelOpen(false);
    setState("idle");
    setEmergency(false);
    setErrorMessage(null);
    setTranscript("");
    setResponseText("");
    setIntentLabel("");
  }, [cleanupStream, closeWs]);

  const speak = useCallback(
    (text: string, code: VoiceSpeechCode) =>
      new Promise<void>((resolve) => {
        if (!text.trim()) {
          resolve();
          return;
        }
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        u.lang = code;
        u.onend = () => resolve();
        u.onerror = () => resolve();
        window.speechSynthesis.speak(u);
      }),
    [],
  );

  const handleIntentPayload = useCallback(
    async (data: IntentWsPayload) => {
      const intent = String(data.intent ?? "unknown");
      const action = String(data.action ?? "none");
      const path = data.action_params?.path;
      const reply = String(data.response_text ?? "");
      const code = speechCodeRef.current;

      setIntentLabel(intent.replace(/_/g, " "));
      setResponseText(reply);

      const isEmergency = intent === "emergency" || action === "trigger_emergency";
      if (isEmergency) {
        setEmergency(true);
      }

      setState("speaking");
      await speak(reply, code);

      if (action === "navigate" && path && typeof path === "string") {
        navigate(path);
      }

      setState("idle");
      closeWs();
    },
    [navigate, speak, closeWs],
  );

  useEffect(
    () => () => {
      window.speechSynthesis.cancel();
      cleanupStream();
      closeWs();
    },
    [cleanupStream, closeWs],
  );

  const startListening = useCallback(async () => {
    if (!patientId.trim()) {
      setErrorMessage("Set VITE_DEFAULT_PATIENT_ID or sign in to use voice.");
      setState("error");
      setPanelOpen(true);
      return;
    }

    window.speechSynthesis.cancel();
    cleanupStream();
    closeWs();

    setPanelOpen(true);
    setEmergency(false);
    setErrorMessage(null);
    setTranscript("");
    setResponseText("");
    setIntentLabel("");
    setState("listening");

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setErrorMessage("Microphone permission denied.");
      setState("error");
      return;
    }
    streamRef.current = stream;

    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${proto}//${window.location.host}/ws/voice/${encodeURIComponent(patientId)}`;
    const ws = new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "config", language: backendLanguage }));
    };

    ws.onmessage = async (ev) => {
      try {
        const data = JSON.parse(String(ev.data)) as
          | { type: string; text?: string; message?: string }
          | IntentWsPayload;
        if (data.type === "transcription") {
          setTranscript(String((data as { text?: string }).text ?? ""));
          setState("processing");
        }
        if (data.type === "intent") {
          await handleIntentPayload(data as IntentWsPayload);
        }
        if (data.type === "error") {
          setErrorMessage(String((data as { message?: string }).message ?? "Voice error"));
          setState("error");
          cleanupStream();
          closeWs();
        }
      } catch {
        setErrorMessage("Bad message from server.");
        setState("error");
        cleanupStream();
        closeWs();
      }
    };

    ws.onerror = () => {
      setErrorMessage("WebSocket error.");
      setState("error");
      cleanupStream();
      closeWs();
    };

    ws.onclose = () => {
      wsRef.current = null;
    };

    const mime = pickRecorderMime();
    const recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
    recorderRef.current = recorder;

    recorder.ondataavailable = async (e) => {
      if (e.data.size > 0) {
        if (ws.readyState === WebSocket.OPEN) {
          const buf = await e.data.arrayBuffer();
          ws.send(buf);
        }
      }
    };

    const finishUtterance = () => {
      stopSilenceRef.current?.();
      stopSilenceRef.current = null;
      if (recorder.state === "recording") {
        recorder.stop();
      }
      recorderRef.current = null;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };

    stopSilenceRef.current = createSilenceDetector(stream, finishUtterance, {
      minMsBeforeArm: 900,
      silenceMs: 1500,
      threshold: 10,
    });

    recorder.start(250);
  }, [backendLanguage, patientId, cleanupStream, closeWs, handleIntentPayload]);

  const examples = VOICE_EXAMPLES[speechCode];

  return {
    state,
    panelOpen,
    transcript,
    responseText,
    intentLabel,
    emergency,
    errorMessage,
    speechCode,
    setSpeechCode,
    examples,
    startListening,
    dismissPanel,
    acknowledgeEmergency,
  };
}
