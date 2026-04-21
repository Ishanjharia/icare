const prefix = "icare_med_taken_";

export function todayKey(): string {
  return new Date().toISOString().slice(0, 10);
}

export function isMedTakenToday(medicationId: number): boolean {
  return localStorage.getItem(`${prefix}${todayKey()}_${medicationId}`) === "1";
}

export function setMedTakenToday(medicationId: number, taken: boolean): void {
  const k = `${prefix}${todayKey()}_${medicationId}`;
  if (taken) localStorage.setItem(k, "1");
  else localStorage.removeItem(k);
}
