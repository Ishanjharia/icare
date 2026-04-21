import { useEffect } from "react";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import { AppLayout } from "./components/layout/AppLayout";
import { Spinner } from "./components/ui/Spinner";
import { healthCheck } from "./services/api";
import { Alerts } from "./pages/Alerts";
import { Appointments } from "./pages/Appointments";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Medications } from "./pages/Medications";
import { Prescriptions } from "./pages/Prescriptions";
import { Records } from "./pages/Records";
import { SymptomChecker } from "./pages/SymptomChecker";
import { Vitals } from "./pages/Vitals";
import { VoiceMode } from "./pages/VoiceMode";
import { Simulator } from "./pages/Simulator";

function HealthWake() {
  useEffect(() => {
    void healthCheck().catch(() => {});
  }, []);
  return null;
}

function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const loc = useLocation();
  if (isLoading) {
    return <Spinner label="Checking your session…" />;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: loc }} />;
  }
  return <Outlet />;
}

function GuestRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) {
    return <Spinner label="Checking your session…" />;
  }
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}

export default function App() {
  return (
    <>
      <HealthWake />
      <Routes>
        <Route element={<GuestRoute />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Route>
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/vitals" element={<Vitals />} />
            <Route path="/symptoms" element={<SymptomChecker />} />
            <Route path="/voice" element={<VoiceMode />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/appointments" element={<Appointments />} />
            <Route path="/records" element={<Records />} />
            <Route path="/prescriptions" element={<Prescriptions />} />
            <Route path="/medications" element={<Medications />} />
            <Route path="/simulator" element={<Simulator />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
