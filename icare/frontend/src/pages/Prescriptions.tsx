import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useActivePatient } from "../hooks/useActivePatient";
import { useAuth } from "../hooks/useAuth";
import { createPrescription, fetchPrescriptionPdfBlob, fetchPrescriptions } from "../services/api";

export function Prescriptions() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const { patientId, ready, isDoctor } = useActivePatient();
  const enabled = ready && Boolean(patientId);

  const listQ = useQuery({
    queryKey: ["prescriptions", patientId],
    queryFn: () => fetchPrescriptions(patientId),
    enabled,
  });

  const [medication, setMedication] = useState("");
  const [dosage, setDosage] = useState("");
  const [instructions, setInstructions] = useState("");

  const createMut = useMutation({
    mutationFn: () =>
      createPrescription({
        patient_id: patientId,
        medication: medication.trim(),
        dosage: dosage.trim(),
        instructions: instructions.trim(),
        language: user?.language ?? "English",
        doctor_name: user?.name ?? null,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["prescriptions", patientId] });
      setMedication("");
      setDosage("");
      setInstructions("");
    },
  });

  const download = async (id: number) => {
    const blob = await fetchPrescriptionPdfBlob(id);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `prescription_${id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!enabled) {
    return (
      <div className="rounded-2xl border border-amber-400/40 bg-amber-50 p-6 text-center text-sm text-amber-800">
        Select a patient to view prescriptions.
      </div>
    );
  }

  const rows = listQ.data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Prescriptions</h1>
        <p className="mt-1 text-sm text-gray-600">PDFs use your logged-in session (no query token).</p>
      </div>

      {isDoctor ? (
        <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-card md:p-6">
          <h2 className="text-sm font-semibold text-gray-900">Prescribe (doctor)</h2>
          <form
            className="mt-4 grid gap-3 sm:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              createMut.mutate();
            }}
          >
            <div className="sm:col-span-2">
              <label className="text-xs font-medium text-gray-600">Medication</label>
              <input
                required
                className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3"
                value={medication}
                onChange={(e) => setMedication(e.target.value)}
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
              <label className="text-xs font-medium text-gray-600">Instructions</label>
              <input
                required
                className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3"
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
              />
            </div>
            <div className="sm:col-span-2">
              <button
                type="submit"
                disabled={createMut.isPending}
                className="min-h-11 rounded-xl bg-teal-400 px-5 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-50"
              >
                {createMut.isPending ? "Saving…" : "Create prescription"}
              </button>
            </div>
          </form>
        </section>
      ) : (
        <p className="text-sm text-gray-600">Patients can view prescriptions issued by their doctor.</p>
      )}

      <section className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-card">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-teal-50/60 text-xs uppercase text-teal-900">
              <tr>
                <th className="px-4 py-3">Medication</th>
                <th className="px-4 py-3">Dosage</th>
                <th className="px-4 py-3">Doctor</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">PDF</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    No prescriptions.
                  </td>
                </tr>
              ) : (
                rows.map((r) => (
                  <tr key={r.id} className="border-t border-gray-100">
                    <td className="px-4 py-3 font-medium">{r.medication}</td>
                    <td className="px-4 py-3 text-gray-700">{r.dosage}</td>
                    <td className="px-4 py-3 text-gray-600">{r.doctor_name ?? "—"}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-gray-600">{new Date(r.created_at).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        className="min-h-11 rounded-lg bg-gray-900 px-3 text-xs font-semibold text-white hover:bg-gray-800"
                        onClick={() => void download(r.id)}
                      >
                        Download
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
