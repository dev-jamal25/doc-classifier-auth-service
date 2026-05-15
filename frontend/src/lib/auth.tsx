import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { MockUser } from "../types";

const STORAGE_KEY = "doc-classifier.mockUser";

type AuthContextValue = {
  user: MockUser | null;
  login: (email: string, password: string) => Promise<MockUser>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const readStoredUser = (): MockUser | null => {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as MockUser) : null;
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
};

const writeStoredUser = (user: MockUser) => {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
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

        const mockUser: MockUser = {
          id: "mock-admin-user",
          email: trimmedEmail,
          roles: ["admin"],
        };

        writeStoredUser(mockUser);
        setUser(mockUser);
        return mockUser;
      },
      logout() {
        window.localStorage.removeItem(STORAGE_KEY);
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
