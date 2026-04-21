import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { useActivePatient } from "../../hooks/useActivePatient";
import { Logo } from "../ui/Logo";
import { VoiceButton } from "../voice/VoiceButton";

const navMain: { to: string; label: string; end?: boolean }[] = [
  { to: "/", label: "Home", end: true },
  { to: "/vitals", label: "Vitals" },
  { to: "/symptoms", label: "Symptoms" },
  { to: "/voice", label: "Voice" },
  { to: "/alerts", label: "Alerts" },
  { to: "/appointments", label: "Appointments" },
  { to: "/records", label: "Records" },
  { to: "/prescriptions", label: "Prescriptions" },
  { to: "/medications", label: "Medications" },
];

const bottomNav: { to: string; label: string; end?: boolean }[] = [
  { to: "/", label: "Home", end: true },
  { to: "/vitals", label: "Vitals" },
  { to: "/symptoms", label: "Symptoms" },
  { to: "/voice", label: "Voice" },
  { to: "/alerts", label: "Alerts" },
];

const bottomIcons = [HomeIcon, HeartIcon, ChatIcon, MicIcon, BellIcon] as const;

function navClass({ isActive }: { isActive: boolean }): string {
  return [
    "flex min-h-11 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
    isActive ? "bg-teal-50 text-teal-800" : "text-gray-700 hover:bg-gray-50",
  ].join(" ");
}

function bottomClass({ isActive }: { isActive: boolean }): string {
  return [
    "flex min-h-11 min-w-[44px] flex-1 flex-col items-center justify-center gap-0.5 py-1 text-xs font-medium",
    isActive ? "text-teal-600" : "text-gray-500",
  ].join(" ");
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { patientId, setPatientId, isDoctor } = useActivePatient();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [draftPatient, setDraftPatient] = useState(patientId);

  useEffect(() => {
    if (drawerOpen) setDraftPatient(patientId);
  }, [drawerOpen, patientId]);

  const onSavePatient = () => {
    setPatientId(draftPatient);
    setDrawerOpen(false);
  };

  return (
    <div className="min-h-screen bg-[#F9FAFB] text-gray-900">
      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex items-center gap-2 border-b border-gray-200 bg-white px-3 py-2 lg:hidden">
        <button
          type="button"
          className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-gray-700 hover:bg-gray-50"
          aria-label="Open menu"
          onClick={() => setDrawerOpen(true)}
        >
          <MenuIcon />
        </button>
        <Link to="/" className="min-h-11 flex-1" onClick={() => setDrawerOpen(false)}>
          <Logo />
        </Link>
        <VoiceButton patientId={patientId} />
      </header>

      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col border-r border-[#E5E7EB] bg-white lg:flex">
        <div className="flex h-14 items-center border-b border-[#E5E7EB] px-4">
          <Link to="/" className="min-h-11">
            <Logo />
          </Link>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
          {navMain.map((item) => (
            <NavLink key={item.to} to={item.to} end={Boolean(item.end)} className={navClass}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-[#E5E7EB] p-3">
          {isDoctor ? (
            <div>
              <label className="block text-xs font-medium text-gray-500">Patient UUID</label>
              <input
                className="mt-1 w-full rounded-lg border border-gray-200 px-2 py-2 text-xs"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                placeholder="Paste patient UUID"
              />
            </div>
          ) : (
            <p className="truncate text-xs text-gray-500" title={user?.email}>
              {user?.name}
              <span className="mt-0.5 block text-[11px] capitalize text-teal-700">{user?.role}</span>
            </p>
          )}
          <div className="mt-3 flex items-center justify-between gap-2">
            <VoiceButton patientId={patientId} />
            <button
              type="button"
              className="min-h-11 rounded-lg px-3 text-sm font-medium text-gray-600 hover:bg-gray-50"
              onClick={() => {
                logout();
                navigate("/login", { replace: true });
              }}
            >
              Log out
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile drawer */}
      {drawerOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true">
          <button
            type="button"
            className="absolute inset-0 bg-black/40"
            aria-label="Close menu"
            onClick={() => setDrawerOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 flex w-64 max-w-[85vw] flex-col border-r border-[#E5E7EB] bg-white shadow-xl">
            <div className="flex h-14 items-center justify-between border-b border-[#E5E7EB] px-3">
              <Logo />
              <button
                type="button"
                className="min-h-11 min-w-11 rounded-lg text-gray-600 hover:bg-gray-50"
                aria-label="Close"
                onClick={() => setDrawerOpen(false)}
              >
                ✕
              </button>
            </div>
            <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
              {navMain.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={Boolean(item.end)}
                  className={navClass}
                  onClick={() => setDrawerOpen(false)}
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
            <div className="border-t border-[#E5E7EB] p-3">
              {isDoctor ? (
                <>
                  <label className="text-xs font-medium text-gray-500">Patient UUID</label>
                  <input
                    className="mt-1 w-full rounded-lg border border-gray-200 px-2 py-2 text-xs"
                    value={draftPatient}
                    onChange={(e) => setDraftPatient(e.target.value)}
                    placeholder="Paste patient UUID"
                  />
                  <button
                    type="button"
                    className="mt-2 w-full min-h-11 rounded-lg bg-teal-400 px-3 text-sm font-semibold text-white"
                    onClick={onSavePatient}
                  >
                    Apply
                  </button>
                </>
              ) : null}
              <button
                type="button"
                className="mt-3 w-full min-h-11 rounded-lg border border-gray-200 text-sm font-medium text-gray-700"
                onClick={() => {
                  logout();
                  setDrawerOpen(false);
                  navigate("/login", { replace: true });
                }}
              >
                Log out
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="lg:pl-64">
        <main className="mx-auto max-w-6xl px-3 pb-24 pt-4 md:px-6 lg:pb-8">
          <Outlet />
        </main>
      </div>

      {/* Mobile bottom navigation */}
      <nav className="fixed bottom-0 left-0 right-0 z-30 flex border-t border-[#E5E7EB] bg-white px-1 pb-[max(0.25rem,env(safe-area-inset-bottom))] pt-1 shadow-[0_-4px_12px_rgba(0,0,0,0.06)] lg:hidden">
        {bottomNav.map((item, index) => {
          const Icon = bottomIcons[index];
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={Boolean(item.end)}
              className={bottomClass}
              onClick={() => setDrawerOpen(false)}
            >
              <Icon />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
    </div>
  );
}

function MenuIcon() {
  return (
    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

function HomeIcon() {
  return (
    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    </svg>
  );
}

function HeartIcon() {
  return (
    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
    </svg>
  );
}

function MicIcon() {
  return (
    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
    </svg>
  );
}
