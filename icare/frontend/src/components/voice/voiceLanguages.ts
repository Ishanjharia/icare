export type VoiceSpeechCode =
  | "hi-IN"
  | "en-IN"
  | "mr-IN"
  | "ta-IN"
  | "te-IN"
  | "bn-IN"
  | "gu-IN"
  | "kn-IN"
  | "ml-IN"
  | "pa-IN";

export const VOICE_LANGUAGES: {
  code: VoiceSpeechCode;
  label: string;
  backendLanguage: string;
}[] = [
  { code: "hi-IN", label: "हिन्दी", backendLanguage: "Hindi" },
  { code: "en-IN", label: "English", backendLanguage: "English" },
  { code: "mr-IN", label: "मराठी", backendLanguage: "Marathi" },
  { code: "ta-IN", label: "தமிழ்", backendLanguage: "Tamil" },
  { code: "te-IN", label: "తెలుగు", backendLanguage: "Telugu" },
  { code: "bn-IN", label: "বাংলা", backendLanguage: "Bengali" },
  { code: "gu-IN", label: "ગુજરાતી", backendLanguage: "Gujarati" },
  { code: "kn-IN", label: "ಕನ್ನಡ", backendLanguage: "Kannada" },
  { code: "ml-IN", label: "മലയാളം", backendLanguage: "Malayalam" },
  { code: "pa-IN", label: "ਪੰਜਾਬੀ", backendLanguage: "Punjabi" },
];

export const VOICE_EXAMPLES: Record<VoiceSpeechCode, string[]> = {
  "hi-IN": [
    "“वाइटल्स दिखाओ”",
    "“लक्षण चेक करो”",
    "“अपॉइंटमेंट खोलो”",
    "“दवाइयाँ दिखाओ”",
  ],
  "en-IN": [
    "“Show vitals”",
    "“Open symptom checker”",
    "“Open appointments”",
    "“Show my medications”",
  ],
  "mr-IN": [
    "“व्हायटल्स दाखवा”",
    "“लक्षण तपासा”",
    "“अपॉइंटमेंट उघडा”",
    "“औषधे दाखवा”",
  ],
  "ta-IN": [
    "“வைட்டல்ஸ் காட்டு”",
    "“அறிகுறிகளை சரிபார்”",
    "“நேரம் குறிப்பு”",
    "“மருந்துகள்”",
  ],
  "te-IN": [
    "“వైటల్స్ చూపించు”",
    "“లక్షణాలు తనిఖీ”",
    "“అపాయింట్‌మెంట్‌లు”",
    "“మందులు”",
  ],
  "bn-IN": [
    "“ভাইটালস দেখাও”",
    "“লক্ষণ পরীক্ষা”",
    "“অ্যাপয়েন্টমেন্ট”",
    "“ওষুধ”",
  ],
  "gu-IN": [
    "“વાઇટલ્સ બતાવો”",
    "“લક્ષણો તપાસો”",
    "“અપોઇન્ટમેન્ટ”",
    "“દવાઓ”",
  ],
  "kn-IN": [
    "“ವೈಟಲ್ಸ್ ತೋರಿಸಿ”",
    "“ಲಕ್ಷಣಗಳು”",
    "“ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್”",
    "“ಔಷಧಿಗಳು”",
  ],
  "ml-IN": [
    "“വൈറ്റൽസ് കാണിക്കുക”",
    "“ലക്ഷണങ്ങൾ”",
    "“അപ്പോയിന്റ്മെന്റ്”",
    "“മരുന്നുകൾ”",
  ],
  "pa-IN": [
    "“ਵਾਇਟਲਸ ਦਿਖਾਓ”",
    "“ਲੱਛਣ ਚੈਕ ਕਰੋ”",
    "“ਅਪਾਇੰਟਮੈਂਟ”",
    "“ਦਵਾਈਆਂ”",
  ],
};
