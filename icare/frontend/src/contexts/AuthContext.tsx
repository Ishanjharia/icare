import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  fetchMe,
  loginRequest,
  registerRequest,
  setStoredToken,
  getStoredToken,
  type User,
  type UserRole,
} from "../services/api";

type AuthContextValue = {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    name: string;
    email: string;
    password: string;
    role: UserRole;
    language: string;
    phone?: string | null;
  }) => Promise<void>;
  logout: () => void;
  refetchUser: () => Promise<User | undefined>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [token, setTokenState] = useState<string | null>(() => getStoredToken());

  const meQuery = useQuery({
    queryKey: ["auth", "me", token],
    queryFn: fetchMe,
    enabled: Boolean(token),
    retry: false,
    staleTime: 60_000,
  });

  const user = meQuery.data ?? null;
  const isLoading = Boolean(token) && meQuery.isLoading;

  useEffect(() => {
    const on401 = () => {
      setTokenState(null);
      queryClient.removeQueries({ queryKey: ["auth", "me"] });
    };
    window.addEventListener("icare-auth-401", on401);
    return () => window.removeEventListener("icare-auth-401", on401);
  }, [queryClient]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await loginRequest(email, password);
      setStoredToken(res.access_token);
      setTokenState(res.access_token);
      queryClient.setQueryData(["auth", "me", res.access_token], res.user);
    },
    [queryClient],
  );

  const register = useCallback(
    async (payload: {
      name: string;
      email: string;
      password: string;
      role: UserRole;
      language: string;
      phone?: string | null;
    }) => {
      await registerRequest(payload);
      await login(payload.email, payload.password);
    },
    [login],
  );

  const logout = useCallback(() => {
    setStoredToken(null);
    setTokenState(null);
    queryClient.removeQueries({ queryKey: ["auth", "me"] });
    queryClient.clear();
  }, [queryClient]);

  const refetchUser = useCallback(async () => {
    if (!getStoredToken()) return undefined;
    const t = getStoredToken()!;
    const r = await queryClient.fetchQuery({ queryKey: ["auth", "me", t], queryFn: fetchMe });
    return r;
  }, [queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isLoading,
      isAuthenticated: Boolean(user),
      login,
      register,
      logout,
      refetchUser,
    }),
    [user, token, isLoading, login, register, logout, refetchUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
