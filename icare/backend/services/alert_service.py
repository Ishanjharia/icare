"""5-level vitals alert escalation with Fast2SMS and WebSocket broadcasts."""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings
from database import async_session_factory
from models.alert import Alert
from models.health_profile import HealthProfile
from models.user import User
from schemas.alert import AlertOut, PipelineStatus, PipelineStep
from services.vitals_service import DEFAULT_THRESHOLDS, compute_alert_level, normalize_metric

logger = logging.getLogger(__name__)

# Same numeric thresholds as vitals_service.DEFAULT_THRESHOLDS
THRESHOLDS: dict[str, dict[str, float]] = DEFAULT_THRESHOLDS

ALERT_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "heart_rate_high": "Warning: Your heart rate is {value} bpm. Normal is below 100 bpm.",
        "spo2_low": "Warning: Your blood oxygen is {value}%. Seek medical attention below 94%.",
        "critical": "EMERGENCY: Critical vital signs detected. Seek immediate medical care. Call 102.",
    },
    "hi": {
        "heart_rate_high": "चेतावनी: आपकी हृदय गति {value} bpm है। सामान्य 100 से कम होनी चाहिए।",
        "spo2_low": "चेतावनी: आपका रक्त ऑक्सीजन {value}% है। 94% से नीचे डॉक्टर से मिलें।",
        "critical": "आपातकाल: गंभीर स्वास्थ्य संकेत। तुरंत चिकित्सा सहायता लें। 102 पर कॉल करें।",
    },
}

# Seconds to wait while at ``level`` before moving to ``level + 1``
ESCALATION_DELAY_SECONDS: dict[int, int] = {
    1: 60,
    2: 120,
    3: 180,
    4: 300,
}


def _lang_bucket(user_language: str | None) -> str:
    if user_language and "hindi" in user_language.lower():
        return "hi"
    return "en"


def _template_key(metric: str, value: float, vitals_level: int) -> str:
    if vitals_level >= 5:
        return "critical"
    m = normalize_metric(metric)
    if m == "spo2":
        return "spo2_low"
    return "heart_rate_high"


def _format_message(metric: str, value: float, vitals_level: int, user_language: str | None) -> str:
    bucket = _lang_bucket(user_language)
    key = _template_key(metric, value, vitals_level)
    template = ALERT_MESSAGES[bucket].get(key) or ALERT_MESSAGES["en"][key]
    return template.format(value=value)


def _breach_threshold_value(metric: str, value: float) -> float:
    m = normalize_metric(metric)
    cfg = THRESHOLDS.get(m, {})
    if m in {"heart_rate", "bp_systolic", "bp_diastolic"}:
        ch = cfg.get("critical_high")
        cl = cfg.get("critical_low")
        ah = cfg.get("alert_high")
        wl = cfg.get("warn_low")
        wh = cfg.get("warn_high")
        if ch is not None and value >= ch:
            return float(ch)
        if cl is not None and value <= cl:
            return float(cl)
        if ah is not None and value >= ah:
            return float(ah)
        if wl is not None and value <= wl:
            return float(wl)
        if wh is not None and value >= wh:
            return float(wh)
    if m == "spo2":
        cl = cfg.get("critical_low")
        al = cfg.get("alert_low")
        if cl is not None and value <= cl:
            return float(cl)
        if al is not None and value <= al:
            return float(al)
    return float(value)


def _pipeline_initial_level(vitals_level: int) -> int:
    if vitals_level <= 2:
        return 1
    if vitals_level <= 4:
        return 3
    return 5


def _normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone.strip())
    if len(digits) >= 12 and digits.startswith("91"):
        digits = digits[-10:]
    if len(digits) < 10:
        return None
    return digits


async def _broadcast_alert(patient_id: str, payload: dict[str, Any]) -> None:
    try:
        from services.vitals_ws_manager import vitals_ws_manager

        await vitals_ws_manager.broadcast_to_patient(patient_id, payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("alert WebSocket broadcast failed: %s", exc)


async def _apply_escalation_step(alert_id: uuid.UUID, new_level: int) -> None:
    """Side effects after DB level has been incremented to ``new_level``."""
    async with async_session_factory() as db:
        svc = AlertService(db)
        alert = await db.get(Alert, alert_id)
        if alert is None or alert.acknowledged:
            return
        user = await db.get(User, alert.patient_id)
        user_language = user.language if user else None
        msg = alert.message
        lang = "unicode" if _lang_bucket(user_language) == "hi" else "english"

        if new_level == 2:
            await _broadcast_alert(
                str(alert.patient_id),
                {
                    "type": "alert_escalation",
                    "alert_id": str(alert.id),
                    "level": 2,
                    "message": msg,
                },
            )
            return

        if new_level == 3:
            if user and user.phone and not alert.sms_sent:
                ok = await svc.send_sms(user.phone, msg, language=lang)
                if ok:
                    await db.execute(update(Alert).where(Alert.id == alert.id).values(sms_sent=True))
                    await db.commit()
            return

        if new_level == 4:
            profile = await db.scalar(
                select(HealthProfile).where(HealthProfile.user_id == alert.patient_id),
            )
            if not alert.caregiver_notified:
                care = _normalize_phone(profile.caregiver_phone if profile else None)
                if care:
                    ok = await svc.send_sms(care, msg, language=lang)
                    if ok:
                        await db.execute(
                            update(Alert).where(Alert.id == alert.id).values(caregiver_notified=True),
                        )
                        await db.commit()
            return

        if new_level == 5:
            await svc._send_level5_notifications(db, alert, user_language)
            await db.commit()
            await _broadcast_alert(
                str(alert.patient_id),
                {
                    "type": "emergency",
                    "alert_id": str(alert.id),
                    "level": 5,
                    "message": msg,
                },
            )


async def run_alert_escalation(alert_id: str) -> None:
    """Background entrypoint: owns its own DB sessions across long sleeps."""
    try:
        aid = uuid.UUID(str(alert_id))
    except ValueError:
        logger.warning("run_alert_escalation invalid id: %s", alert_id)
        return

    while True:
        async with async_session_factory() as db:
            alert = await db.get(Alert, aid)
            if alert is None or alert.acknowledged or alert.level >= 5:
                return
            delay = ESCALATION_DELAY_SECONDS.get(alert.level)
            if delay is None:
                return

        await asyncio.sleep(delay)

        async with async_session_factory() as db:
            alert = await db.get(Alert, aid)
            if alert is None or alert.acknowledged:
                return
            if alert.level >= 5:
                return

            new_level = alert.level + 1
            await db.execute(
                update(Alert)
                .where(Alert.id == aid, Alert.acknowledged.is_(False))
                .values(level=new_level),
            )
            await db.commit()

        await _apply_escalation_step(aid, new_level)


class AlertService:
    """Threshold evaluation, SMS (Fast2SMS), escalation, acknowledgements."""

    async def evaluate_reading(
        self,
        db: AsyncSession,
        patient_id: uuid.UUID,
        metric: str,
        value: float,
    ) -> Alert | None:
        canonical = normalize_metric(metric)
        vitals_level = compute_alert_level(canonical, float(value))
        if vitals_level is None:
            return None

        user = await db.get(User, patient_id)
        user_language = user.language if user else None
        msg = _format_message(canonical, float(value), vitals_level, user_language)
        thr = _breach_threshold_value(canonical, float(value))
        initial = _pipeline_initial_level(vitals_level)

        row = Alert(
            patient_id=patient_id,
            vital_type=canonical,
            value=float(value),
            threshold=float(thr),
            level=initial,
            message=msg,
        )
        db.add(row)
        await db.flush()

        await _broadcast_alert(
            str(patient_id),
            {
                "type": "alert",
                "alert_id": str(row.id),
                "vital_type": canonical,
                "value": float(value),
                "level": initial,
                "message": msg,
            },
        )

        if initial >= 5:
            await self._send_level5_notifications(db, row, user_language)
            await db.commit()
            await _broadcast_alert(
                str(patient_id),
                {
                    "type": "emergency",
                    "alert_id": str(row.id),
                    "message": msg,
                    "level": 5,
                },
            )
            return row

        if initial >= 3:
            if user and user.phone:
                ok = await self.send_sms(
                    user.phone,
                    msg,
                    language="unicode" if _lang_bucket(user_language) == "hi" else "english",
                )
                if ok:
                    await db.execute(
                        update(Alert).where(Alert.id == row.id).values(sms_sent=True),
                    )
            await db.commit()
            return row

        await db.commit()
        return row

    async def _send_level5_notifications(
        self,
        db: AsyncSession,
        alert: Alert,
        user_language: str | None,
    ) -> None:
        user = await db.get(User, alert.patient_id)
        profile = await db.scalar(
            select(HealthProfile).where(HealthProfile.user_id == alert.patient_id),
        )
        msg = alert.message
        lang = "unicode" if _lang_bucket(user_language) == "hi" else "english"
        phones: set[str] = set()
        for raw in (
            user.phone if user else None,
            profile.emergency_contact_phone if profile else None,
            profile.caregiver_phone if profile else None,
        ):
            n = _normalize_phone(raw)
            if n:
                phones.add(n)
        for phone in phones:
            await self.send_sms(phone, msg, language=lang)
        await db.execute(
            update(Alert)
            .where(Alert.id == alert.id)
            .values(sms_sent=True, caregiver_notified=True),
        )

    async def send_sms(self, phone: str, message: str, language: str = "english") -> bool:
        normalized = _normalize_phone(phone)
        if not normalized:
            return False
        params = {
            "route": "q",
            "message": message,
            "language": language,
            "flash": 0,
            "numbers": normalized,
        }
        headers = {"authorization": settings.FAST2SMS_API_KEY}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    "https://www.fast2sms.com/dev/bulkV2",
                    headers=headers,
                    params=params,
                )
            if resp.status_code == 200:
                return True
            logger.warning("Fast2SMS non-200: %s %s", resp.status_code, resp.text[:200])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Fast2SMS request failed: %s", exc)
        return False

    async def acknowledge_alert(
        self,
        db: AsyncSession,
        alert_id: str,
        patient_id: uuid.UUID,
    ) -> bool:
        try:
            aid = uuid.UUID(str(alert_id))
        except ValueError:
            return False
        alert = await db.get(Alert, aid)
        if alert is None or alert.patient_id != patient_id:
            return False
        now = datetime.now(timezone.utc)
        await db.execute(
            update(Alert)
            .where(Alert.id == aid)
            .values(acknowledged=True, acknowledged_at=now),
        )
        await db.commit()
        return True

    async def trigger_emergency(self, db: AsyncSession, patient_id: uuid.UUID) -> Alert:
        user = await db.get(User, patient_id)
        user_language = user.language if user else None
        msg = _format_message("heart_rate", 0.0, 5, user_language)
        row = Alert(
            patient_id=patient_id,
            vital_type="emergency",
            value=0.0,
            threshold=0.0,
            level=5,
            message=msg,
            sms_sent=False,
            caregiver_notified=False,
        )
        db.add(row)
        await db.flush()
        await self._send_level5_notifications(db, row, user_language)
        await db.commit()
        await _broadcast_alert(
            str(patient_id),
            {
                "type": "emergency",
                "alert_id": str(row.id),
                "level": 5,
                "message": msg,
                "manual": True,
            },
        )
        await db.refresh(row)
        return row

    async def list_active_unacknowledged(self, db: AsyncSession, patient_id: uuid.UUID) -> list[AlertOut]:
        res = await db.scalars(
            select(Alert)
            .where(Alert.patient_id == patient_id, Alert.acknowledged.is_(False))
            .order_by(Alert.created_at.desc()),
        )
        return [AlertOut.model_validate(a) for a in res.all()]

    async def list_history(self, db: AsyncSession, patient_id: uuid.UUID) -> list[AlertOut]:
        res = await db.scalars(
            select(Alert).where(Alert.patient_id == patient_id).order_by(Alert.created_at.desc()).limit(200),
        )
        return [AlertOut.model_validate(a) for a in res.all()]

    async def pipeline_status(self, db: AsyncSession, patient_id: uuid.UUID) -> PipelineStatus:
        steps = [
            PipelineStep(from_level=1, to_level=2, delay_seconds=60, action="websocket_broadcast"),
            PipelineStep(from_level=2, to_level=3, delay_seconds=120, action="sms_patient"),
            PipelineStep(from_level=3, to_level=4, delay_seconds=180, action="sms_caregiver"),
            PipelineStep(from_level=4, to_level=5, delay_seconds=300, action="sms_all_emergency_contacts"),
        ]
        active = await self.list_active_unacknowledged(db, patient_id)
        return PipelineStatus(patient_id=patient_id, steps=steps, active_alerts=active)

    async def escalate_alert(self, db: AsyncSession, alert_id: str) -> None:
        """Run timed escalation (ignores ``db``; opens its own sessions). Use from BackgroundTasks."""
        _ = db
        await run_alert_escalation(alert_id)
