import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useActivePatient } from "../hooks/useActivePatient";
import { useAuth } from "../hooks/useAuth";
import { createHealthRecord, fetchHealthRecords } from "../services/api";

export function Records() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const { patientId, ready } = useActivePatient();
  const enabled = ready && Boolean(patientId);

  const listQ = useQuery({
    queryKey: ["records", patientId],
    queryFn: () => fetchHealthRecords(patientId),
    enabled,
  });

  const [record_type, setRecordType] = useState("visit");
  const [description, setDescription] = useState("");

  const createMut = useMutation({
    mutationFn: () =>
      createHealthRecord(patientId, {
        record_type: record_type.trim(),
        description: description.trim(),
        language: user?.language ?? "English",
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["records", patientId] });
      setDescription("");
    },
  });

  if (!enabled) {
    return (
      <div className="rounded-2xl border border-amber-400/40 bg-amber-50 p-6 text-center text-sm text-amber-800">
        Select a patient to view health records.
      </div>
    );
  }

  const rows = listQ.data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Health records</h1>
        <p className="mt-1 text-sm text-gray-600">Clinical notes and reports for this patient.</p>
      </div>

      <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-card md:p-6">
        <h2 className="text-sm font-semibold text-gray-900">Add record</h2>
        <form
          className="mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
        >
          <div>
            <label className="text-xs font-medium text-gray-600">Type</label>
            <input
              required
              className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3"
              value={record_type}
              onChange={(e) => setRecordType(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600">Description</label>
            <textarea
              required
              className="mt-1 min-h-24 w-full rounded-lg border border-gray-200 p-3"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <button
            type="submit"
            disabled={createMut.isPending}
            className="min-h-11 rounded-xl bg-teal-400 px-5 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-50"
          >
            {createMut.isPending ? "Saving…" : "Save record"}
          </button>
        </form>
      </section>

      <section className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-card">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-teal-50/60 text-xs uppercase text-teal-900">
              <tr>
                <th className="px-4 py-3">When</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3">Lang</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                    No records yet.
                  </td>
                </tr>
              ) : (
                rows.map((r) => (
                  <tr key={r.id} className="border-t border-gray-100">
                    <td className="whitespace-nowrap px-4 py-3 text-gray-600">{new Date(r.created_at).toLocaleString()}</td>
                    <td className="px-4 py-3 font-medium">{r.record_type}</td>
                    <td className="max-w-md px-4 py-3 text-gray-800">{r.description}</td>
                    <td className="px-4 py-3 text-gray-600">{r.language}</td>
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
