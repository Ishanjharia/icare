import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "./useAuth";

const LS_KEY = "icare_selected_patient_id";

export function useActivePatient(): {
  patientId: string;
  setPatientId: (id: string) => void;
  isDoctor: boolean;
  ready: boolean;
} {
  const { user } = useAuth();
  const envPid = (import.meta.env.VITE_DEFAULT_PATIENT_ID as string | undefined)?.trim() ?? "";
  const [docPatient, setDocPatient] = useState(() => localStorage.getItem(LS_KEY)?.trim() ?? envPid);

  useEffect(() => {
    if (user?.role !== "doctor") return;
    const stored = localStorage.getItem(LS_KEY)?.trim();
    if (stored) {
      setDocPatient(stored);
      return;
    }
    if (envPid) {
      setDocPatient(envPid);
      localStorage.setItem(LS_KEY, envPid);
    }
  }, [user?.role, envPid]);

  const setPatientId = useCallback((id: string) => {
    const v = id.trim();
    setDocPatient(v);
    if (v) localStorage.setItem(LS_KEY, v);
    else localStorage.removeItem(LS_KEY);
  }, []);

  return useMemo(() => {
    if (!user) {
      return { patientId: "", setPatientId, isDoctor: false, ready: false };
    }
    if (user.role === "doctor") {
      return {
        patientId: docPatient,
        setPatientId,
        isDoctor: true,
        ready: true,
      };
    }
    return { patientId: user.id, setPatientId: () => {}, isDoctor: false, ready: true };
  }, [user, docPatient, setPatientId]);
}
