"""Groq LLM orchestration for I-CARE (medical chat, triage, STT, translation)."""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from groq import AsyncGroq

from config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_MEDICAL = """
You are a medical AI assistant for I-CARE, a healthcare system for rural India.
Analyze symptoms and return structured assessments.
Rules:
- Respond in the SAME language the user writes in
- Handle Hindi-English mixed language naturally
- ALWAYS include: "This is not a medical diagnosis. Consult a qualified doctor."
- NEVER recommend specific drug dosages
- If confidence is low (<0.6), explicitly say to consult a doctor immediately
- For Critical severity: say seek emergency care immediately (call 102)
""".strip()

MEDICAL_DISCLAIMER_LINE = (
    "This is not a medical diagnosis. Consult a qualified doctor."
)

EMERGENCY_KEYWORDS = [
    "मदद",
    "help",
    "emergency",
    "bachao",
    "बचाओ",
    "help me",
    "urgent",
    "call doctor",
    "ambulance",
]

_INTENT_SYSTEM = """You classify short voice or text commands for a rural India health app.
Return ONLY valid JSON with exactly these keys: intent (string), confidence (float 0-1), params (object, use {} if none).
intent must be exactly one of:
navigate_symptom_checker, navigate_vitals, navigate_appointments,
navigate_medications, navigate_records, read_vitals, read_last_record,
ask_health_question, book_appointment, set_reminder, emergency, unknown
Do not add other keys or markdown."""

_VALID_INTENTS = frozenset(
    {
        "navigate_symptom_checker",
        "navigate_vitals",
        "navigate_appointments",
        "navigate_medications",
        "navigate_records",
        "read_vitals",
        "read_last_record",
        "ask_health_question",
        "book_appointment",
        "set_reminder",
        "emergency",
        "unknown",
    }
)

_ai_service: AIService | None = None


def get_ai_service() -> AIService:
    """Process-wide AIService singleton."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text


def _parse_json_object(text: str) -> dict[str, Any] | None:
    cleaned = _strip_json_fence(text)
    try:
        out = json.loads(cleaned)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                out = json.loads(cleaned[start : end + 1])
                return out if isinstance(out, dict) else None
            except json.JSONDecodeError:
                return None
    return None


def _normalize_severity(value: Any) -> str:
    if value is None:
        return "Low"
    s = str(value).strip()
    if not s:
        return "Low"
    title = s[0].upper() + s[1:].lower() if len(s) > 1 else s.upper()
    lower = title.lower()
    for allowed in ("Low", "Medium", "High", "Critical"):
        if lower == allowed.lower():
            return allowed
    return "Low"


def _clamp_confidence(value: Any) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, f))


def _str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return []


def _format_profile(health_profile: dict[str, Any] | None) -> str:
    if not health_profile:
        return "None provided."
    lines: list[str] = []
    for key in ("allergies", "conditions", "medications", "notes"):
        v = health_profile.get(key)
        if v:
            lines.append(f"- {key}: {v}")
    if not lines:
        return json.dumps(health_profile, ensure_ascii=False, indent=2)
    return "\n".join(lines)


def _format_vitals(vitals_snapshot: dict[str, Any] | None) -> str:
    if not vitals_snapshot:
        return "None provided."
    hr = vitals_snapshot.get("heart_rate") or vitals_snapshot.get("hr")
    spo2 = vitals_snapshot.get("spo2") or vitals_snapshot.get("SpO2")
    bp = vitals_snapshot.get("blood_pressure") or vitals_snapshot.get("bp")
    parts = []
    if hr is not None:
        parts.append(f"Heart rate: {hr}")
    if spo2 is not None:
        parts.append(f"SpO2: {spo2}")
    if bp is not None:
        parts.append(f"Blood pressure: {bp}")
    if parts:
        return "; ".join(parts)
    return json.dumps(vitals_snapshot, ensure_ascii=False, indent=2)


def _sniff_audio_suffix(data: bytes) -> str:
    """Pick a filename suffix compatible with Groq Whisper for common browser / IoT blobs."""
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return ".wav"
    if len(data) >= 4 and data[:4] == b"\x1a\x45\xdf\xa3":  # EBML (WebM / Matroska)
        return ".webm"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return ".m4a"
    if len(data) >= 2 and data[0] == 0xFF and data[1] in (0xFB, 0xF3, 0xF2):
        return ".mp3"
    return ".webm"


def _symptom_error_payload(message: str) -> dict[str, Any]:
    return {
        "success": False,
        "error": message,
        "severity_level": "Low",
        "urgent_care_needed": False,
        "symptoms_summary": "",
        "possible_conditions": [],
        "recommendations": [],
        "follow_up_questions": [],
        "confidence_score": 0.0,
        "medical_disclaimer": MEDICAL_DISCLAIMER_LINE,
        "escalation_note": None,
        "raw_context": None,
    }


class AIService:
    """Medical chat, symptom triage, translation, STT via Groq."""

    def __init__(self) -> None:
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def _chat_text(
        self,
        *,
        system: str,
        user: str,
        model: str,
        temperature: float,
    ) -> str:
        resp = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_completion_tokens=2048,
        )
        choice = resp.choices[0].message
        return (choice.content or "").strip()

    async def analyze_symptoms(
        self,
        symptoms_text: str,
        language: str,
        health_profile: dict[str, Any] | None = None,
        vitals_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        profile = health_profile or {}
        vitals = vitals_snapshot or {}
        raw_context: dict[str, Any] = {
            "symptoms_excerpt": symptoms_text[:500],
            "has_vitals": bool(vitals),
            "has_profile": bool(profile),
        }
        user_block = f"""Patient-reported symptoms:
{symptoms_text}

Vitals (if any): {_format_vitals(vitals)}

Health profile (allergies, conditions, medications):
{_format_profile(profile)}

Respond in: {language}

Return ONLY valid JSON with exactly these keys:
severity_level (one of: Low, Medium, High, Critical),
urgent_care_needed (boolean),
symptoms_summary (string),
possible_conditions (array of strings),
recommendations (array of strings),
follow_up_questions (array of strings),
confidence_score (number from 0 to 1)

No markdown, no code fences, no extra keys."""

        try:
            content = await self._chat_text(
                system=SYSTEM_PROMPT_MEDICAL,
                user=user_block,
                model=settings.GROQ_MEDICAL_MODEL,
                temperature=0.3,
            )
            parsed = _parse_json_object(content)
            if not parsed:
                out = _symptom_error_payload("Could not parse model response as JSON.")
                out["raw_context"] = raw_context
                return out

            severity = _normalize_severity(parsed.get("severity_level"))
            confidence = _clamp_confidence(parsed.get("confidence_score"))
            urgent = bool(parsed.get("urgent_care_needed"))
            summary = str(parsed.get("symptoms_summary") or "").strip()
            conditions = _str_list(parsed.get("possible_conditions"))
            recs = _str_list(parsed.get("recommendations"))
            questions = _str_list(parsed.get("follow_up_questions"))

            if MEDICAL_DISCLAIMER_LINE.lower() not in summary.lower():
                summary = (
                    f"{summary}\n\n{MEDICAL_DISCLAIMER_LINE}".strip()
                    if summary
                    else MEDICAL_DISCLAIMER_LINE
                )

            result: dict[str, Any] = {
                "success": True,
                "error": None,
                "severity_level": severity,
                "urgent_care_needed": urgent,
                "symptoms_summary": summary,
                "possible_conditions": conditions,
                "recommendations": recs,
                "follow_up_questions": questions,
                "confidence_score": confidence,
                "medical_disclaimer": MEDICAL_DISCLAIMER_LINE,
                "raw_context": raw_context,
            }
            if confidence < 0.6:
                result["escalation_note"] = (
                    "Confidence is low. Please consult a qualified doctor immediately "
                    "for an in-person evaluation."
                )
            else:
                result["escalation_note"] = None

            if severity.lower() == "critical":
                emerg = (
                    "Seek emergency care immediately. In India, you can call 102 "
                    "for ambulance / emergency medical help."
                )
                if not any(emerg.split(".")[0] in r for r in recs):
                    recs = [emerg, *recs]
                result["recommendations"] = recs
                result["urgent_care_needed"] = True

            return result
        except Exception as exc:  # noqa: BLE001
            logger.exception("analyze_symptoms failed: %s", exc)
            out = _symptom_error_payload(str(exc))
            out["raw_context"] = raw_context
            return out

    async def chat_response(
        self,
        message: str,
        language: str,
        role: str,
        health_profile: dict[str, Any],
        history: list[dict[str, str]],
    ) -> AsyncGenerator[str, None]:
        profile_text = _format_profile(health_profile)
        system = f"""{SYSTEM_PROMPT_MEDICAL}

You are assisting as: {role}.
Health context (may be empty):
{profile_text}

Chat rules:
- Respond in the SAME language as the user; target preference: {language}.
- Never give specific drug dosages.
- Include the disclaimer sentence when giving health guidance: {MEDICAL_DISCLAIMER_LINE}
- For possible emergencies, advise immediate in-person care and mention calling 102 in India."""

        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        for turn in history[-24:]:
            r = str(turn.get("role", "")).lower()
            c = str(turn.get("content", ""))
            if r in {"user", "assistant"} and c:
                messages.append({"role": r, "content": c})
        messages.append({"role": "user", "content": message})

        try:
            stream = await self.client.chat.completions.create(
                model=settings.GROQ_MEDICAL_MODEL,
                messages=messages,
                temperature=0.4,
                stream=True,
                max_completion_tokens=2048,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                piece = delta.content if delta and delta.content else None
                if piece:
                    yield piece
        except Exception as exc:  # noqa: BLE001
            logger.exception("chat_response stream failed: %s", exc)
            yield f"\n[{MEDICAL_DISCLAIMER_LINE} Unable to reach the AI service right now. Please try again. ({exc!s})]\n"

    async def classify_intent(self, transcript: str, language: str) -> dict[str, Any]:
        lowered = transcript.lower()
        for kw in EMERGENCY_KEYWORDS:
            if kw.lower() in lowered:
                return {"intent": "emergency", "confidence": 1.0, "params": {}}

        user = f"""Language hint: {language}
User said:
{transcript}
"""
        try:
            content = await self._chat_text(
                system=_INTENT_SYSTEM,
                user=user,
                model=settings.GROQ_FAST_MODEL,
                temperature=0.0,
            )
            parsed = _parse_json_object(content)
            if not parsed:
                return {"intent": "unknown", "confidence": 0.0, "params": {}}
            intent = str(parsed.get("intent", "unknown")).strip()
            if intent not in _VALID_INTENTS:
                intent = "unknown"
            conf = _clamp_confidence(parsed.get("confidence"))
            params = parsed.get("params")
            if not isinstance(params, dict):
                params = {}
            return {"intent": intent, "confidence": conf, "params": params}
        except Exception as exc:  # noqa: BLE001
            logger.exception("classify_intent failed: %s", exc)
            return {"intent": "unknown", "confidence": 0.0, "params": {}}

    async def translate_text(self, text: str, from_lang: str, to_lang: str) -> str:
        system = "Translate accurately. Return ONLY translated text, nothing else."
        user = f"From: {from_lang}\nTo: {to_lang}\nText:\n{text}"
        try:
            return await self._chat_text(
                system=system,
                user=user,
                model=settings.GROQ_FAST_MODEL,
                temperature=0.2,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("translate_text failed: %s", exc)
            return text

    async def generate_prescription_translation(
        self, prescription_text: str, from_lang: str, to_lang: str
    ) -> str:
        system = (
            "You translate prescription and clinical text for patients. "
            "Preserve drug names where appropriate. Return ONLY the translated text, nothing else."
        )
        user = f"From: {from_lang}\nTo: {to_lang}\nPrescription:\n{prescription_text}"
        try:
            return await self._chat_text(
                system=system,
                user=user,
                model=settings.GROQ_MEDICAL_MODEL,
                temperature=0.2,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("generate_prescription_translation failed: %s", exc)
            return prescription_text

    async def find_hospitals(
        self, city: str, specialty: str | None = None, language: str = "English"
    ) -> dict[str, Any]:
        spec = specialty or "general / multi-specialty"
        user = f"""City in India: {city}
Desired specialty filter (optional): {spec}
Language for names/addresses (use Indian context): {language}

Return ONLY valid JSON: {{"hospitals": [ ... exactly 5 objects ... ]}}
Each hospital object must have keys:
name, address, phone, specialties (array of strings), distance_km (number),
rating (number 1-5), emergency (boolean), type (either Government or Private).

Use realistic plausible data for the city. No markdown."""

        try:
            content = await self._chat_text(
                system="You generate structured placeholder hospital listings for a demo health app.",
                user=user,
                model=settings.GROQ_FAST_MODEL,
                temperature=0.5,
            )
            parsed = _parse_json_object(content)
            if not parsed or "hospitals" not in parsed:
                return {"success": False, "error": "Invalid JSON", "hospitals": []}
            hospitals = parsed.get("hospitals")
            if not isinstance(hospitals, list):
                return {"success": False, "error": "hospitals not a list", "hospitals": []}
            return {"success": True, "error": None, "hospitals": hospitals[:5]}
        except Exception as exc:  # noqa: BLE001
            logger.exception("find_hospitals failed: %s", exc)
            return {"success": False, "error": str(exc), "hospitals": []}

    async def transcribe_audio(self, audio_bytes: bytes) -> dict[str, Any]:
        tmp_path: Path | None = None
        try:
            suffix = _sniff_audio_suffix(audio_bytes)
            fd, name = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            tmp_path = Path(name)
            tmp_path.write_bytes(audio_bytes)
            resp = await self.client.audio.transcriptions.create(
                file=tmp_path,
                model=settings.GROQ_WHISPER_MODEL,
                response_format="text",
            )
            if isinstance(resp, str):
                text = resp
            else:
                text = getattr(resp, "text", "") or str(resp)
            return {
                "success": True,
                "transcription": text.strip(),
                "detected_language": "",
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception("transcribe_audio failed: %s", exc)
            return {
                "success": False,
                "transcription": "",
                "detected_language": "",
                "error": str(exc),
            }
        finally:
            if tmp_path is not None:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass
