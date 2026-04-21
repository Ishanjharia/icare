import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useActivePatient } from "../hooks/useActivePatient";
import { createMedication, fetchMedications, updateMedication, type Medication } from "../services/api";

export function Medications() {
  const qc = useQueryClient();
  const { patientId, ready } = useActivePatient();
  const enabled = ready && Boolean(patientId);

  const listQ = useQuery({
    queryKey: ["medications", patientId],
    queryFn: () => fetchMedications(patientId),
    enabled,
  });

  const [name, setName] = useState("");
  const [dosage, setDosage] = useState("");
  const [frequency, setFrequency] = useState("");
  const [notes, setNotes] = useState("");

  const createMut = useMutation({
    mutationFn: () =>
      createMedication({
        patient_id: patientId,
        name: name.trim(),
        dosage: dosage.trim(),
        frequency: frequency.trim(),
        notes: notes.trim() || null,
        status: "active",
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["medications", patientId] });
      setName("");
      setDosage("");
      setFrequency("");
      setNotes("");
    },
  });

  const updateMut = useMutation({
    mutationFn: (p: { id: number; patch: Partial<Medication> }) => updateMedication(p.id, p.patch),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["medications", patientId] }),
  });

  if (!enabled) {
    return (
      <div className="rounded-2xl border border-amber-400/40 bg-amber-50 p-6 text-center text-sm text-amber-800">
        Select a patient to manage medications.
      </div>
    );
  }

  const rows = listQ.data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Medications</h1>
        <p className="mt-1 text-sm text-gray-600">List and update the care plan.</p>
      </div>

      <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-card md:p-6">
        <h2 className="text-sm font-semibold text-gray-900">Add medication</h2>
        <form
          className="mt-4 grid gap-3 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
        >
          <div className="sm:col-span-2">
            <label className="text-xs font-medium text-gray-600">Name</label>
            <input
              required
              className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600">Dosage</label>
            <input
              required
              className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3"
              value={dosage}
              onChange={(e) => setDosage(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600">Frequency</label>
            <input
              required
              className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3"
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs font-medium text-gray-600">Notes</label>
            <textarea
              className="mt-1 min-h-20 w-full rounded-lg border border-gray-200 p-3"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={createMut.isPending}
              className="min-h-11 rounded-xl bg-teal-400 px-5 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-50"
            >
              {createMut.isPending ? "Saving…" : "Add"}
            </button>
          </div>
        </form>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold text-gray-900">Current list</h2>
        {rows.length === 0 ? (
          <p className="rounded-xl border border-gray-100 bg-white p-6 text-center text-sm text-gray-500 shadow-card">
            No medications yet.
          </p>
        ) : (
          rows.map((m) => (
            <MedicationEditor key={m.id} med={m} disabled={updateMut.isPending} onSave={(patch) => updateMut.mutate({ id: m.id, patch })} />
          ))
        )}
      </section>
    </div>
  );
}

function MedicationEditor({
  med,
  onSave,
  disabled,
}: {
  med: Medication;
  onSave: (patch: Partial<Medication>) => void;
  disabled: boolean;
}) {
  const [name, setName] = useState(med.name);
  const [dosage, setDosage] = useState(med.dosage);
  const [frequency, setFrequency] = useState(med.frequency);
  const [status, setStatus] = useState(med.status);
  const [notes, setNotes] = useState(med.notes ?? "");

  return (
    <article className="rounded-2xl border border-gray-100 bg-white p-4 shadow-card">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="text-xs font-medium text-gray-600">Name</label>
          <input className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="text-xs font-medium text-gray-600">Dosage</label>
          <input className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3" value={dosage} onChange={(e) => setDosage(e.target.value)} />
        </div>
        <div>
          <label className="text-xs font-medium text-gray-600">Frequency</label>
          <input
            className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3"
            value={frequency}
            onChange={(e) => setFrequency(e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs font-medium text-gray-600">Status</label>
          <select className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="active">active</option>
            <option value="paused">paused</option>
            <option value="ended">ended</option>
          </select>
        </div>
        <div className="sm:col-span-2">
          <label className="text-xs font-medium text-gray-600">Notes</label>
          <textarea className="mt-1 min-h-16 w-full rounded-lg border border-gray-200 p-3" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <button
        type="button"
        className="mt-4 min-h-11 rounded-xl bg-teal-400 px-4 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-50"
        disabled={disabled}
        onClick={() =>
          onSave({
            name: name.trim(),
            dosage: dosage.trim(),
            frequency: frequency.trim(),
            status,
            notes: notes.trim() || null,
          })
        }
      >
        Save changes
      </button>
    </article>
  );
}
