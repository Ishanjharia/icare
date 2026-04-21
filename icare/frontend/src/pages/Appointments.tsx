import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useActivePatient } from "../hooks/useActivePatient";
import { useAuth } from "../hooks/useAuth";
import { createAppointment, fetchAppointments } from "../services/api";

export function Appointments() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const { patientId, ready } = useActivePatient();
  const enabled = ready && Boolean(patientId);

  const listQ = useQuery({
    queryKey: ["appointments", patientId],
    queryFn: () => fetchAppointments(patientId),
    enabled,
  });

  const [appt_date, setApptDate] = useState("");
  const [appt_time, setApptTime] = useState("");
  const [doctor_name, setDoctorName] = useState("");
  const [notes, setNotes] = useState("");

  const createMut = useMutation({
    mutationFn: () =>
      createAppointment({
        patient_id: patientId,
        doctor_name: doctor_name.trim() || user?.name || "Doctor",
        appt_date,
        appt_time,
        notes: notes.trim() || null,
        language: user?.language ?? "English",
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["appointments", patientId] });
      setNotes("");
    },
  });

  if (!enabled) {
    return (
      <div className="rounded-2xl border border-amber-400/40 bg-amber-50 p-6 text-center text-sm text-amber-800">
        Select a patient to manage appointments.
      </div>
    );
  }

  const rows = listQ.data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Appointments</h1>
        <p className="mt-1 text-sm text-gray-600">Schedule and review visits.</p>
      </div>

      <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-card md:p-6">
        <h2 className="text-sm font-semibold text-gray-900">New appointment</h2>
        <form
          className="mt-4 grid gap-3 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
        >
          <div>
            <label className="text-xs font-medium text-gray-600">Date</label>
            <input
              required
              type="date"
              className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3"
              value={appt_date}
              onChange={(e) => setApptDate(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600">Time</label>
            <input
              required
              type="time"
              className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3"
              value={appt_time}
              onChange={(e) => setApptTime(e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs font-medium text-gray-600">Doctor name</label>
            <input
              className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3"
              value={doctor_name}
              onChange={(e) => setDoctorName(e.target.value)}
              placeholder={user?.name ?? "Dr. …"}
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
              {createMut.isPending ? "Saving…" : "Create"}
            </button>
          </div>
        </form>
      </section>

      <section className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-card">
        <div className="border-b border-gray-100 px-4 py-3">
          <h2 className="text-sm font-semibold text-gray-900">Upcoming &amp; past</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-teal-50/60 text-xs uppercase text-teal-900">
              <tr>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Doctor</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Notes</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    No appointments yet.
                  </td>
                </tr>
              ) : (
                rows.map((r) => (
                  <tr key={r.id} className="border-t border-gray-100">
                    <td className="px-4 py-3">{r.appt_date}</td>
                    <td className="px-4 py-3">{r.appt_time}</td>
                    <td className="px-4 py-3">{r.doctor_name ?? "—"}</td>
                    <td className="px-4 py-3 capitalize">{r.status}</td>
                    <td className="max-w-xs truncate px-4 py-3 text-gray-600">{r.notes ?? "—"}</td>
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
