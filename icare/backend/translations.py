"""
UI translations (Arogyamitra-style i18n for I-CARE).

The original Arogyamitra Streamlit ``translations`` module is not vendored in this
repository; this file preserves the same *API* (``TRANSLATIONS``, ``get_text``,
``get_greeting``, ``get_nav_items``, ``export_all``) with a broad **en** / **hi**
string table suitable for rural India. When the upstream dict is available, merge
rows into ``_TRANSLATION_ROWS`` without changing the public helpers below.
"""

from __future__ import annotations

from typing import Any, Final

# (key, english, hindi)
_TRANSLATION_ROWS: Final[list[tuple[str, str, str]]] = [
    ("app_title", "I-CARE", "आई-केयर"),
    ("app_tagline", "Rural digital health", "ग्रामीण डिजिटल स्वास्थ्य"),
    ("greeting_hello", "Hello", "नमस्ते"),
    ("greeting_welcome", "Welcome to I-CARE", "आई-केयर में आपका स्वागत है"),
    ("btn_save", "Save", "सहेजें"),
    ("btn_cancel", "Cancel", "रद्द करें"),
    ("btn_submit", "Submit", "जमा करें"),
    ("btn_next", "Next", "आगे"),
    ("btn_back", "Back", "पीछे"),
    ("btn_close", "Close", "बंद करें"),
    ("btn_download", "Download", "डाउनलोड"),
    ("btn_login", "Log in", "लॉग इन"),
    ("btn_logout", "Log out", "लॉग आउट"),
    ("btn_register", "Register", "पंजीकरण"),
    ("nav_home", "Home", "होम"),
    ("nav_dashboard", "Dashboard", "डैशबोर्ड"),
    ("nav_vitals", "Vitals", "वाइटल्स"),
    ("nav_symptoms", "Symptom checker", "लक्षण जाँच"),
    ("nav_voice", "Voice", "आवाज़"),
    ("nav_alerts", "Alerts", "अलर्ट"),
    ("nav_appointments", "Appointments", "अपॉइंटमेंट"),
    ("nav_records", "Records", "रिकॉर्ड"),
    ("nav_prescriptions", "Prescriptions", "प्रिस्क्रिप्शन"),
    ("nav_medications", "Medications", "दवाइयाँ"),
    ("nav_chat", "Health chat", "स्वास्थ्य चैट"),
    ("nav_hospitals", "Hospitals", "अस्पताल"),
    ("nav_settings", "Settings", "सेटिंग्स"),
    ("nav_doctor_panel", "Doctor panel", "डॉक्टर पैनल"),
    ("auth_email", "Email", "ईमेल"),
    ("auth_password", "Password", "पासवर्ड"),
    ("auth_name", "Full name", "पूरा नाम"),
    ("auth_phone", "Phone", "फ़ोन"),
    ("auth_forgot", "Forgot password?", "पासवर्ड भूल गए?"),
    ("vitals_title", "Vitals", "वाइटल्स"),
    ("vitals_hr", "Heart rate", "हृदय गति"),
    ("vitals_spo2", "Blood oxygen (SpO2)", "रक्त ऑक्सीजन"),
    ("vitals_bp", "Blood pressure", "रक्तचाप"),
    ("vitals_last_reading", "Last reading", "आखिरी रीडिंग"),
    ("symptoms_title", "Symptom checker", "लक्षण जाँच"),
    ("symptoms_placeholder", "Describe your symptoms", "अपने लक्षण बताएँ"),
    ("symptoms_analyze", "Analyze", "विश्लेषण"),
    ("symptoms_disclaimer", "Not a diagnosis — see a doctor.", "निदान नहीं — डॉक्टर से मिलें।"),
    ("records_title", "Health records", "स्वास्थ्य रिकॉर्ड"),
    ("records_new", "New record", "नया रिकॉर्ड"),
    ("records_type", "Record type", "रिकॉर्ड प्रकार"),
    ("records_description", "Description", "विवरण"),
    ("prescriptions_title", "Prescriptions", "प्रिस्क्रिप्शन"),
    ("prescriptions_medication", "Medication", "दवा"),
    ("prescriptions_dosage", "Dosage", "खुराक"),
    ("prescriptions_instructions", "Instructions", "निर्देश"),
    ("appointments_title", "Appointments", "अपॉइंटमेंट"),
    ("appointments_date", "Date", "तारीख"),
    ("appointments_time", "Time", "समय"),
    ("appointments_status", "Status", "स्थिति"),
    ("appointments_scheduled", "Scheduled", "निर्धारित"),
    ("appointments_completed", "Completed", "पूर्ण"),
    ("appointments_cancelled", "Cancelled", "रद्द"),
    ("medications_title", "Medications", "दवाइयाँ"),
    ("medications_name", "Name", "नाम"),
    ("medications_frequency", "Frequency", "बारंबारता"),
    ("medications_active", "Active", "सक्रिय"),
    ("medications_completed", "Completed", "पूर्ण"),
    ("alerts_title", "Alerts", "अलर्ट"),
    ("alerts_acknowledge", "Acknowledge", "स्वीकार"),
    ("chat_title", "Chat", "चैट"),
    ("voice_title", "Voice assistant", "आवाज़ सहायक"),
    ("hospitals_title", "Hospitals", "अस्पताल"),
    ("pdf_prescription", "Prescription PDF", "प्रिस्क्रिप्शन पीडीएफ"),
    ("pdf_health_record", "Health record PDF", "स्वास्थ्य रिकॉर्ड पीडीएफ"),
    ("error_generic", "Something went wrong.", "कुछ गलत हो गया।"),
    ("error_unauthorized", "Please sign in.", "कृपया साइन इन करें।"),
    ("error_forbidden", "You do not have access.", "आपके पास पहुँच नहीं है।"),
    ("error_not_found", "Not found.", "नहीं मिला।"),
    ("success_saved", "Saved successfully.", "सफलतापूर्वक सहेजा गया।"),
    ("language_english", "English", "अंग्रेज़ी"),
    ("language_hindi", "Hindi", "हिन्दी"),
    ("role_patient", "Patient", "मरीज़"),
    ("role_doctor", "Doctor", "डॉक्टर"),
    ("role_caregiver", "Caregiver", "देखभालकर्ता"),
    ("health_context_title", "AI health context", "एआई स्वास्थ्य संदर्भ"),
    ("footer_powered", "Powered by Groq & Supabase", "Groq और Supabase द्वारा संचालित"),
]

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {k: en for k, en, _hi in _TRANSLATION_ROWS},
    "hi": {k: hi for k, _en, hi in _TRANSLATION_ROWS},
}

_NAV_PATIENT: Final[list[tuple[str, str]]] = [
    ("/", "nav_home"),
    ("/vitals", "nav_vitals"),
    ("/symptoms", "nav_symptoms"),
    ("/voice", "nav_voice"),
    ("/alerts", "nav_alerts"),
    ("/appointments", "nav_appointments"),
    ("/records", "nav_records"),
    ("/prescriptions", "nav_prescriptions"),
    ("/medications", "nav_medications"),
]

_NAV_DOCTOR: Final[list[tuple[str, str]]] = [
    ("/", "nav_dashboard"),
    ("/vitals", "nav_vitals"),
    ("/symptoms", "nav_symptoms"),
    ("/appointments", "nav_appointments"),
    ("/records", "nav_records"),
    ("/prescriptions", "nav_prescriptions"),
    ("/medications", "nav_medications"),
    ("/voice", "nav_voice"),
    ("/alerts", "nav_alerts"),
]


def _norm_lang(language: str) -> str:
    l = (language or "en").strip().lower()
    if l.startswith("hi") or "hindi" in l:
        return "hi"
    return "en"


def get_text(key: str, language: str = "en") -> str:
    """Return localized UI string for ``key`` (falls back to English, then the key)."""
    lang = _norm_lang(language)
    bundle = TRANSLATIONS.get(lang) or TRANSLATIONS["en"]
    if key in bundle:
        return bundle[key]
    return TRANSLATIONS["en"].get(key, key)


def get_greeting(language: str) -> str:
    """Short greeting for dashboards / headers."""
    return get_text("greeting_welcome", language)


def get_nav_items(role: str, language: str) -> list[dict[str, str]]:
    """Sidebar-style navigation: ``href`` + localized ``label``."""
    lang = _norm_lang(language)
    r = (role or "patient").strip().lower()
    keys = _NAV_DOCTOR if r == "doctor" else _NAV_PATIENT
    return [{"href": href, "label": get_text(label_key, lang)} for href, label_key in keys]


def export_all() -> dict[str, Any]:
    """Export translation bundle for tooling / frontend bootstrap."""
    return {"translations": TRANSLATIONS, "keys": sorted(TRANSLATIONS["en"].keys())}
