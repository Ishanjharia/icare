"""Health records, prescriptions, appointments, medications — CRUD + AI context."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.appointment import Appointment
from models.health_profile import HealthProfile
from models.health_record import HealthRecord
from models.medication import Medication
from models.prescription import Prescription
from schemas.appointment import AppointmentCreate, AppointmentResponse, AppointmentUpdate
from schemas.health_record import HealthRecordResponse
from schemas.medication import MedicationCreate, MedicationResponse, MedicationUpdate
from schemas.prescription import PrescriptionCreate, PrescriptionResponse


class RecordsService:
    """CRUD for clinical artifacts."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # --- Health records ---
    async def add_health_record(
        self,
        db: AsyncSession,
        patient_id: uuid.UUID,
        record_type: str,
        description: str,
        language: str,
        report_data: dict[str, Any] | None = None,
        vitals_snapshot: dict[str, Any] | None = None,
    ) -> HealthRecord:
        row = HealthRecord(
            patient_id=patient_id,
            record_type=record_type,
            description=description,
            language=language,
            report_data=report_data,
            vitals_snapshot=vitals_snapshot,
        )
        db.add(row)
        await db.flush()
        return row

    async def create_health_record(
        self,
        *,
        patient_id: uuid.UUID,
        record_type: str,
        description: str,
        language: str,
        report_data: dict[str, Any] | None = None,
        vitals_snapshot: dict[str, Any] | None = None,
    ) -> HealthRecordResponse:
        row = await self.add_health_record(
            self._db,
            patient_id,
            record_type,
            description,
            language,
            report_data=report_data,
            vitals_snapshot=vitals_snapshot,
        )
        await self._db.commit()
        await self._db.refresh(row)
        return HealthRecordResponse.model_validate(row)

    async def list_health_records(self, patient_id: uuid.UUID, *, limit: int = 200) -> list[HealthRecordResponse]:
        q = (
            select(HealthRecord)
            .where(HealthRecord.patient_id == patient_id)
            .order_by(desc(HealthRecord.created_at))
            .limit(limit)
        )
        rows = (await self._db.scalars(q)).all()
        return [HealthRecordResponse.model_validate(r) for r in rows]

    SYMPTOM_RECORD_TYPES = ("symptom_analysis", "symptom_checker", "symptoms")

    async def list_symptom_analysis_records(
        self,
        patient_id: uuid.UUID,
        *,
        limit: int = 200,
    ) -> list[HealthRecordResponse]:
        q = (
            select(HealthRecord)
            .where(
                HealthRecord.patient_id == patient_id,
                HealthRecord.record_type.in_(self.SYMPTOM_RECORD_TYPES),
            )
            .order_by(desc(HealthRecord.created_at))
            .limit(limit)
        )
        rows = (await self._db.scalars(q)).all()
        return [HealthRecordResponse.model_validate(r) for r in rows]

    async def get_health_record(self, record_id: int, patient_id: uuid.UUID) -> HealthRecord | None:
        row = await self._db.get(HealthRecord, record_id)
        if row is None or row.patient_id != patient_id:
            return None
        return row

    async def delete_health_record(self, record_id: int, patient_id: uuid.UUID) -> bool:
        row = await self.get_health_record(record_id, patient_id)
        if row is None:
            return False
        await self._db.delete(row)
        await self._db.commit()
        return True

    async def get_health_context_for_ai(self, db: AsyncSession, patient_id: uuid.UUID) -> dict[str, Any]:
        """Compact bundle for LLM prompts (symptom history, profile, meds, last visit)."""
        profile_row = await db.scalar(select(HealthProfile).where(HealthProfile.user_id == patient_id))
        profile: dict[str, Any] = {}
        if profile_row:
            profile = {
                "blood_type": profile_row.blood_type,
                "allergies": profile_row.allergies,
                "chronic_conditions": profile_row.chronic_conditions,
                "current_medications": profile_row.current_medications,
            }

        sym_types = ("symptom_analysis", "symptom_checker", "symptoms")
        rec_q = (
            select(HealthRecord)
            .where(
                HealthRecord.patient_id == patient_id,
                HealthRecord.record_type.in_(sym_types),
            )
            .order_by(desc(HealthRecord.created_at))
            .limit(3)
        )
        recent = (await db.scalars(rec_q)).all()
        recent_records: list[dict[str, Any]] = []
        for r in recent:
            recent_records.append(
                {
                    "record_type": r.record_type,
                    "description": r.description[:800],
                    "language": r.language,
                    "report_data": r.report_data,
                    "created_at": r.created_at.isoformat(),
                },
            )

        med_q = (
            select(Medication)
            .where(Medication.patient_id == patient_id, Medication.status == "active")
            .order_by(desc(Medication.created_at))
            .limit(50)
        )
        meds = (await db.scalars(med_q)).all()
        active_medications = [
            {
                "name": m.name,
                "dosage": m.dosage,
                "frequency": m.frequency,
                "notes": m.notes,
            }
            for m in meds
        ]

        ap_q = (
            select(Appointment)
            .where(Appointment.patient_id == patient_id)
            .order_by(desc(Appointment.appt_date), desc(Appointment.appt_time))
            .limit(1)
        )
        last_ap = (await db.scalars(ap_q)).first()
        last_appointment: dict[str, Any] | None = None
        if last_ap:
            last_appointment = {
                "doctor_name": last_ap.doctor_name,
                "date": last_ap.appt_date.isoformat(),
                "time": last_ap.appt_time.isoformat(),
                "status": last_ap.status,
                "notes": last_ap.notes,
            }

        return {
            "profile": profile,
            "recent_records": recent_records,
            "active_medications": active_medications,
            "last_appointment": last_appointment,
        }

    # --- Prescriptions ---
    async def list_prescriptions(self, patient_id: uuid.UUID) -> list[PrescriptionResponse]:
        q = select(Prescription).where(Prescription.patient_id == patient_id).order_by(desc(Prescription.created_at))
        rows = (await self._db.scalars(q)).all()
        return [PrescriptionResponse.model_validate(r) for r in rows]

    async def get_prescription(self, prescription_id: int) -> Prescription | None:
        return await self._db.get(Prescription, prescription_id)

    async def create_prescription(self, data: PrescriptionCreate, *, doctor_name: str | None = None) -> PrescriptionResponse:
        row = Prescription(
            patient_id=data.patient_id,
            doctor_id=data.doctor_id,
            doctor_name=doctor_name or data.doctor_name,
            medication=data.medication,
            dosage=data.dosage,
            instructions=data.instructions,
            language=data.language,
            translated_text=data.translated_text,
        )
        self._db.add(row)
        await self._db.commit()
        await self._db.refresh(row)
        return PrescriptionResponse.model_validate(row)

    async def delete_prescription(self, prescription_id: int, patient_id: uuid.UUID) -> bool:
        row = await self._db.get(Prescription, prescription_id)
        if row is None or row.patient_id != patient_id:
            return False
        await self._db.delete(row)
        await self._db.commit()
        return True

    # --- Appointments ---
    async def list_appointments(self, patient_id: uuid.UUID) -> list[AppointmentResponse]:
        q = select(Appointment).where(Appointment.patient_id == patient_id).order_by(desc(Appointment.appt_date))
        rows = (await self._db.scalars(q)).all()
        return [AppointmentResponse.model_validate(r) for r in rows]

    async def get_appointment(self, appointment_id: int, patient_id: uuid.UUID) -> Appointment | None:
        row = await self._db.get(Appointment, appointment_id)
        if row is None or row.patient_id != patient_id:
            return None
        return row

    async def create_appointment(
        self,
        data: AppointmentCreate,
        *,
        doctor_name: str | None = None,
    ) -> AppointmentResponse:
        row = Appointment(
            patient_id=data.patient_id,
            doctor_id=data.doctor_id,
            doctor_name=doctor_name or data.doctor_name,
            appt_date=data.appt_date,
            appt_time=data.appt_time,
            status=data.status,
            language=data.language,
            notes=data.notes,
        )
        self._db.add(row)
        await self._db.commit()
        await self._db.refresh(row)
        return AppointmentResponse.model_validate(row)

    async def update_appointment(
        self,
        appointment_id: int,
        patient_id: uuid.UUID,
        data: AppointmentUpdate,
    ) -> AppointmentResponse | None:
        row = await self.get_appointment(appointment_id, patient_id)
        if row is None:
            return None
        patch = data.model_dump(exclude_unset=True)
        for k, v in patch.items():
            setattr(row, k, v)
        await self._db.commit()
        await self._db.refresh(row)
        return AppointmentResponse.model_validate(row)

    async def delete_appointment(self, appointment_id: int, patient_id: uuid.UUID) -> bool:
        row = await self.get_appointment(appointment_id, patient_id)
        if row is None:
            return False
        await self._db.delete(row)
        await self._db.commit()
        return True

    # --- Medications ---
    async def list_medications(self, patient_id: uuid.UUID) -> list[MedicationResponse]:
        q = select(Medication).where(Medication.patient_id == patient_id).order_by(desc(Medication.created_at))
        rows = (await self._db.scalars(q)).all()
        return [MedicationResponse.model_validate(r) for r in rows]

    async def get_medication_by_id(self, medication_id: int) -> Medication | None:
        return await self._db.get(Medication, medication_id)

    async def get_medication(self, medication_id: int, patient_id: uuid.UUID) -> Medication | None:
        row = await self._db.get(Medication, medication_id)
        if row is None or row.patient_id != patient_id:
            return None
        return row

    async def create_medication(self, data: MedicationCreate) -> MedicationResponse:
        row = Medication(
            patient_id=data.patient_id,
            name=data.name,
            dosage=data.dosage,
            frequency=data.frequency,
            start_date=data.start_date,
            end_date=data.end_date,
            status=data.status,
            notes=data.notes,
        )
        self._db.add(row)
        await self._db.commit()
        await self._db.refresh(row)
        return MedicationResponse.model_validate(row)

    async def update_medication(
        self,
        medication_id: int,
        patient_id: uuid.UUID,
        data: MedicationUpdate,
    ) -> MedicationResponse | None:
        row = await self.get_medication(medication_id, patient_id)
        if row is None:
            return None
        patch = data.model_dump(exclude_unset=True)
        for k, v in patch.items():
            setattr(row, k, v)
        await self._db.commit()
        await self._db.refresh(row)
        return MedicationResponse.model_validate(row)

    async def delete_medication(self, medication_id: int, patient_id: uuid.UUID) -> bool:
        row = await self.get_medication(medication_id, patient_id)
        if row is None:
            return False
        await self._db.delete(row)
        await self._db.commit()
        return True


def get_records_service(db: AsyncSession) -> RecordsService:
    return RecordsService(db)
