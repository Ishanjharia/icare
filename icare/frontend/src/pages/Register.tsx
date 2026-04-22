import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import type { AxiosError } from "axios";
import { api, setStoredToken, type TokenResponse } from "../services/api";

export default function Register() {
  const [role, setRole] = useState("patient");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const formData = new FormData(e.currentTarget);
    const name = String(formData.get("name") ?? "").trim();
    const email = String(formData.get("email") ?? "").trim();
    const password = String(formData.get("password") ?? "");
    const data = {
      name,
      email,
      password,
      role,
      language: "English",
      phone: "",
    };

    try {
      await api.post("/api/auth/register", data);
      const loginRes = await api.post<TokenResponse>("/api/auth/login", { email, password });
      if (loginRes.data.access_token) {
        setStoredToken(loginRes.data.access_token);
        window.location.assign("/dashboard");
      } else {
        setError("Registration failed");
      }
    } catch (err) {
      const ax = err as AxiosError<{ detail?: string }>;
      const detail = ax.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Cannot connect to server. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#f0fdf4",
      }}
    >
      <div
        style={{
          background: "white",
          padding: "2rem",
          borderRadius: "12px",
          width: "100%",
          maxWidth: "400px",
          boxShadow: "0 4px 20px rgba(0,0,0,0.1)",
        }}
      >
        <h1 style={{ textAlign: "center", color: "#1D9E75", marginBottom: "0.5rem" }}>I-CARE</h1>
        <h2 style={{ textAlign: "center", marginBottom: "1.5rem", fontWeight: "normal" }}>Create Account</h2>

        {error && (
          <div
            style={{
              background: "#fee2e2",
              color: "#dc2626",
              padding: "0.75rem",
              borderRadius: "8px",
              marginBottom: "1rem",
              fontSize: "14px",
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "14px" }}>Full Name</label>
            <input
              name="name"
              required
              placeholder="Your name"
              style={{
                width: "100%",
                padding: "10px",
                border: "1px solid #ddd",
                borderRadius: "8px",
                fontSize: "16px",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "14px" }}>Email</label>
            <input
              name="email"
              type="email"
              required
              placeholder="your@email.com"
              style={{
                width: "100%",
                padding: "10px",
                border: "1px solid #ddd",
                borderRadius: "8px",
                fontSize: "16px",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "14px" }}>Password</label>
            <input
              name="password"
              type="password"
              required
              placeholder="Min 6 characters"
              minLength={6}
              style={{
                width: "100%",
                padding: "10px",
                border: "1px solid #ddd",
                borderRadius: "8px",
                fontSize: "16px",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div style={{ marginBottom: "1.5rem" }}>
            <label style={{ display: "block", marginBottom: "8px", fontSize: "14px" }}>I am a:</label>
            <div style={{ display: "flex", gap: "10px" }}>
              <button
                type="button"
                onClick={() => setRole("patient")}
                style={{
                  flex: 1,
                  padding: "10px",
                  background: role === "patient" ? "#1D9E75" : "white",
                  color: role === "patient" ? "white" : "#333",
                  border: "1px solid #1D9E75",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontSize: "16px",
                }}
              >
                Patient
              </button>
              <button
                type="button"
                onClick={() => setRole("doctor")}
                style={{
                  flex: 1,
                  padding: "10px",
                  background: role === "doctor" ? "#1D9E75" : "white",
                  color: role === "doctor" ? "white" : "#333",
                  border: "1px solid #1D9E75",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontSize: "16px",
                }}
              >
                Doctor
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "12px",
              background: loading ? "#9ca3af" : "#1D9E75",
              color: "white",
              border: "none",
              borderRadius: "8px",
              fontSize: "16px",
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Creating account..." : "Register"}
          </button>
        </form>

        <p style={{ textAlign: "center", marginTop: "1rem", fontSize: "14px" }}>
          Already have an account?{" "}
          <Link to="/login" style={{ color: "#1D9E75", fontWeight: 600, textDecoration: "none" }}>
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
