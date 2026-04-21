"""Groq Whisper STT on server; TTS is browser Web Speech API only."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from services.ai_service import get_ai_service

logger = logging.getLogger(__name__)

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

_INTENT_PATHS: dict[str, str] = {
    "navigate_symptom_checker": "/symptoms",
    "navigate_vitals": "/vitals",
    "navigate_appointments": "/appointments",
    "navigate_medications": "/medications",
    "navigate_records": "/records",
    "read_vitals": "/vitals",
    "read_last_record": "/records",
    "ask_health_question": "/symptoms",
    "book_appointment": "/appointments",
    "set_reminder": "/appointments",
}

# Short user-facing lines for Web Speech in the browser (en + hi; other langs fall back to en).
_INTENT_MESSAGES: dict[str, dict[str, str]] = {
    "navigate_symptom_checker": {
        "en": "Opening the symptom checker for you.",
        "hi": "मैं लक्षण जाँच खोल रहा हूँ।",
    },
    "navigate_vitals": {
        "en": "Opening your vitals page.",
        "hi": "मैं आपके वाइटल्स पेज पर ले जा रहा हूँ।",
    },
    "navigate_appointments": {
        "en": "Opening appointments.",
        "hi": "मैं अपॉइंटमेंट्स खोल रहा हूँ।",
    },
    "navigate_medications": {
        "en": "Opening your medications list.",
        "hi": "मैं दवाइयों की सूची खोल रहा हूँ।",
    },
    "navigate_records": {
        "en": "Opening your health records.",
        "hi": "मैं आपके स्वास्थ्य रिकॉर्ड खोल रहा हूँ।",
    },
    "read_vitals": {
        "en": "Here are your vitals. Check the screen for the latest readings.",
        "hi": "आपके वाइटल्स स्क्रीन पर दिख रहे हैं। नवीनतम रीडिंग देखें।",
    },
    "read_last_record": {
        "en": "Opening your latest health record.",
        "hi": "मैं आपका ताज़ा स्वास्थ्य रिकॉर्ड दिखा रहा हूँ।",
    },
    "ask_health_question": {
        "en": "You can describe symptoms on the next screen, or ask your question there.",
        "hi": "अगले पेज पर अपने लक्षण लिखें या सवाल पूछें।",
    },
    "book_appointment": {
        "en": "Opening appointments so you can book a visit.",
        "hi": "अपॉइंटमेंट बुक करने के लिए पेज खोल रहा हूँ।",
    },
    "set_reminder": {
        "en": "Opening appointments where you can set visit reminders.",
        "hi": "याद दिलाने के लिए अपॉइंटमेंट्स खोल रहा हूँ।",
    },
    "emergency": {
        "en": (
            "This sounds like an emergency. Stay calm. If it is life-threatening, "
            "call one zero two for an ambulance in India, or go to the nearest emergency department."
        ),
        "hi": (
            "यह आपातकाल जैसा लगता है। शांत रहें। जान खतरे में हो तो भारत में एम्बुलेंस के लिए "
            "एक शून्य दो कॉल करें, या नज़दीकी इमरजेंसी विभाग जाएँ।"
        ),
    },
    "unknown": {
        "en": "Sorry, I did not catch that. Try a short command like show vitals or open symptoms.",
        "hi": "माफ़ करें, समझ नहीं आया। छोटा सा कमांड दोहराएँ, जैसे वाइटल्स दिखाओ या लक्षण खोलो।",
    },
}

_voice_service: VoiceService | None = None


def get_voice_service() -> VoiceService:
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService()
    return _voice_service


def _lang_code(language: str) -> str:
    l = (language or "").strip().lower()
    mapping = (
        ("hindi", "hi"),
        ("english", "en"),
        ("marathi", "mr"),
        ("tamil", "ta"),
        ("telugu", "te"),
        ("bengali", "bn"),
        ("gujarati", "gu"),
        ("kannada", "kn"),
        ("malayalam", "ml"),
        ("punjabi", "pa"),
    )
    for needle, code in mapping:
        if needle in l or l == code:
            return code
    if len(l) >= 2 and l[:2] in {"hi", "en", "mr", "ta", "te", "bn", "gu", "kn", "ml", "pa"}:
        return l[:2]
    return "en"


def _msg(intent: str, language: str) -> str:
    code = _lang_code(language)
    row = _INTENT_MESSAGES.get(intent) or _INTENT_MESSAGES["unknown"]
    return row.get(code) or row.get("en") or ""


def _has_emergency_keyword(transcript: str) -> bool:
    lowered = transcript.lower()
    return any(kw.lower() in lowered for kw in EMERGENCY_KEYWORDS)


class VoiceService:
    """Speech-to-text on server (Groq Whisper); spoken replies play in the browser."""

    async def transcribe_audio(self, audio_bytes: bytes) -> dict[str, Any]:
        """Transcribe audio using Groq Whisper."""
        return await get_ai_service().transcribe_audio(audio_bytes)

    async def process_voice_command(
        self,
        audio_bytes: bytes,
        patient_id: uuid.UUID | str,
        language: str,
    ) -> dict[str, Any]:
        """
        Transcribe, detect emergency phrases, classify intent, and return text for browser TTS.
        """
        _ = patient_id  # reserved for future patient-scoped answers (vitals/records)
        st = await self.transcribe_audio(audio_bytes)
        if not st.get("success"):
            err = str(st.get("error", "transcription failed"))
            logger.warning("voice transcribe failed: %s", err)
            return {
                "transcript": "",
                "intent": "unknown",
                "confidence": 0.0,
                "action": "none",
                "action_params": {},
                "response_text": _msg("unknown", language),
            }

        transcript = str(st.get("transcription", "")).strip()

        if not transcript:
            return {
                "transcript": "",
                "intent": "unknown",
                "confidence": 0.0,
                "action": "none",
                "action_params": {},
                "response_text": _msg("unknown", language),
            }

        if _has_emergency_keyword(transcript):
            return {
                "transcript": transcript,
                "intent": "emergency",
                "confidence": 1.0,
                "action": "trigger_emergency",
                "action_params": {},
                "response_text": _msg("emergency", language),
            }

        classified = await get_ai_service().classify_intent(transcript, language)
        intent = str(classified.get("intent", "unknown"))
        confidence = float(classified.get("confidence") or 0.0)
        params = classified.get("params")
        if not isinstance(params, dict):
            params = {}

        if intent == "emergency":
            return {
                "transcript": transcript,
                "intent": "emergency",
                "confidence": confidence,
                "action": "trigger_emergency",
                "action_params": params,
                "response_text": _msg("emergency", language),
            }

        if intent == "unknown":
            return {
                "transcript": transcript,
                "intent": "unknown",
                "confidence": confidence,
                "action": "none",
                "action_params": params,
                "response_text": _msg("unknown", language),
            }

        path = _INTENT_PATHS.get(intent)
        if path:
            action_params: dict[str, Any] = {"path": path}
            action_params.update(params)
            return {
                "transcript": transcript,
                "intent": intent,
                "confidence": confidence,
                "action": "navigate",
                "action_params": action_params,
                "response_text": _msg(intent, language)
                if intent in _INTENT_MESSAGES
                else _msg("unknown", language),
            }

        return {
            "transcript": transcript,
            "intent": intent,
            "confidence": confidence,
            "action": "respond",
            "action_params": params,
            "response_text": _msg("unknown", language),
        }
