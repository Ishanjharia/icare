import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Logo } from "../components/ui/Logo";
import type { UserRole } from "../services/api";

const LANGUAGES = [
  { code: "English", label: "English" },
  { code: "Hindi", label: "हिन्दी (Hindi)" },
  { code: "Marathi", label: "मराठी (Marathi)" },
  { code: "Tamil", label: "தமிழ் (Tamil)" },
  { code: "Telugu", label: "తెలుగు (Telugu)" },
  { code: "Bengali", label: "বাংলা (Bengali)" },
  { code: "Gujarati", label: "ગુજરાતી (Gujarati)" },
  { code: "Kannada", label: "ಕನ್ನಡ (Kannada)" },
  { code: "Malayalam", label: "മലയാളം (Malayalam)" },
  { code: "Punjabi", label: "ਪੰਜਾਬੀ (Punjabi)" },
] as const;

export function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("patient");
  const [language, setLanguage] = useState<string>("English");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await register({
        name: name.trim(),
        email: email.trim(),
        password,
        role,
        language,
        phone: phone.trim() || null,
      });
      navigate("/", { replace: true });
    } catch {
      setError("Could not register. Try a different email.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#F9FAFB] px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-gray-100 bg-white p-8 shadow-card">
        <div className="flex justify-center">
          <Logo />
        </div>
        <h1 className="mt-6 text-center text-xl font-semibold text-gray-900">Create account</h1>
        <p className="mt-1 text-center text-sm text-gray-600">Choose your role and preferred language.</p>

        <form className="mt-8 space-y-4" onSubmit={onSubmit}>
          <div>
            <label className="text-sm font-medium text-gray-700">Full name</label>
            <input
              required
              className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3 text-base outline-none ring-teal-400 focus:ring-2"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              required
              className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3 text-base outline-none ring-teal-400 focus:ring-2"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Password</label>
            <input
              type="password"
              required
              minLength={6}
              className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3 text-base outline-none ring-teal-400 focus:ring-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div>
            <span className="text-sm font-medium text-gray-700">Role</span>
            <div className="mt-2 grid grid-cols-2 gap-2">
              {(["patient", "doctor"] as const).map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setRole(r)}
                  className={`min-h-11 rounded-xl border px-3 text-sm font-semibold capitalize transition-colors ${
                    role === r
                      ? "border-teal-400 bg-teal-50 text-teal-800"
                      : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label htmlFor="lang" className="text-sm font-medium text-gray-700">
              Language
            </label>
            <select
              id="lang"
              className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 bg-white px-3 text-base outline-none ring-teal-400 focus:ring-2"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Phone (optional)</label>
            <input
              type="tel"
              className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3 text-base outline-none ring-teal-400 focus:ring-2"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>
          {error ? <p className="text-sm text-danger-400">{error}</p> : null}
          <button
            type="submit"
            disabled={busy}
            className="w-full min-h-11 rounded-xl bg-teal-400 px-4 text-sm font-semibold text-white shadow-sm hover:bg-teal-600 disabled:opacity-60"
          >
            {busy ? "Creating…" : "Register"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-600">
          Already have an account?{" "}
          <Link to="/login" className="font-semibold text-teal-600 hover:text-teal-800">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
