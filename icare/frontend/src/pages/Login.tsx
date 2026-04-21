import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Logo } from "../components/ui/Logo";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const loc = useLocation();
  const from = (loc.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch {
      const api = (import.meta.env.VITE_API_URL as string | undefined)?.trim();
      if (import.meta.env.PROD && !api) {
        setError("This deployment is missing VITE_API_URL (set it in Vercel to your API origin).");
      } else {
        setError("Invalid email or password, or the API could not be reached.");
      }
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
        <h1 className="mt-6 text-center text-xl font-semibold text-gray-900">Sign in</h1>
        <p className="mt-1 text-center text-sm text-gray-600">I-CARE cloud — secure access to your care data.</p>

        <form className="mt-8 space-y-4" onSubmit={onSubmit}>
          <div>
            <label htmlFor="email" className="text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3 text-base outline-none ring-teal-400 focus:ring-2"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="password" className="text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              className="mt-1 w-full min-h-11 rounded-lg border border-gray-200 px-3 text-base outline-none ring-teal-400 focus:ring-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error ? <p className="text-sm text-danger-400">{error}</p> : null}
          <button
            type="submit"
            disabled={busy}
            className="w-full min-h-11 rounded-xl bg-teal-400 px-4 text-sm font-semibold text-white shadow-sm hover:bg-teal-600 disabled:opacity-60"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-600">
          New here?{" "}
          <Link to="/register" className="font-semibold text-teal-600 hover:text-teal-800">
            Create an account
          </Link>
        </p>
        {import.meta.env.PROD && !(import.meta.env.VITE_API_URL as string | undefined)?.trim() ? (
          <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-center text-xs text-amber-900 ring-1 ring-amber-200">
            Configure <strong className="font-mono">VITE_API_URL</strong> in Vercel (your Render API base URL, no trailing slash).
          </p>
        ) : null}
      </div>
    </div>
  );
}
