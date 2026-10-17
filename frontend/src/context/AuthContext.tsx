import { createContext, useContext, useState, useEffect } from "react";

interface User {
  name: string;
  email: string;
  role: "citizen" | "worker" | "admin";
}

interface AuthContextValue {
  user: User | null;
  login: (user: User, token: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    // Hydrate from localStorage on first load
    try {
      const stored = localStorage.getItem("civicfix_user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  function login(userData: User, token: string) {
    // Ensure role is persisted — callers pass the role from the API response
    localStorage.setItem("civicfix_user", JSON.stringify(userData));
    localStorage.setItem("civicfix_token", token);
    setUser(userData);
  }

  function logout() {
    localStorage.removeItem("civicfix_user");
    localStorage.removeItem("civicfix_token");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
