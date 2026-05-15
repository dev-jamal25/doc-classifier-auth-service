import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { MockUser } from "../types";
import { apiFetch, clearToken, setToken } from "./apiClient";

const USER_KEY = "doc-classifier.user";

type AuthContextValue = {
  user: MockUser | null;
  login: (email: string, password: string) => Promise<MockUser>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const readStoredUser = (): MockUser | null => {
  try {
    const raw = window.localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as MockUser) : null;
  } catch {
    window.localStorage.removeItem(USER_KEY);
    return null;
  }
};

const writeStoredUser = (user: MockUser) => {
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
};

export const getStoredMockUser = () => readStoredUser();

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MockUser | null>(() => readStoredUser());

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      async login(email: string, password: string) {
        const trimmedEmail = email.trim();
        if (!trimmedEmail || !password.trim()) {
          throw new Error("Email and password are required.");
        }

        const formData = new URLSearchParams();
        formData.set("username", trimmedEmail);
        formData.set("password", password);

        const loginRes = await fetch("/auth/login", {
          method: "POST",
          body: formData,
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        });

        if (!loginRes.ok) {
          throw new Error("Invalid credentials.");
        }

        const { access_token } = (await loginRes.json()) as { access_token: string };
        setToken(access_token);

        const meRes = await apiFetch("/me");
        if (!meRes.ok) {
          clearToken();
          throw new Error("Unable to load user profile.");
        }

        const apiUser = (await meRes.json()) as { id: string; email: string; roles: string[] };

        const mockUser: MockUser = {
          id: apiUser.id,
          email: apiUser.email,
          roles: (apiUser.roles ?? []) as MockUser["roles"],
        };

        writeStoredUser(mockUser);
        setUser(mockUser);
        return mockUser;
      },
      logout() {
        clearToken();
        window.localStorage.removeItem(USER_KEY);
        setUser(null);
      },
    }),
    [user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
