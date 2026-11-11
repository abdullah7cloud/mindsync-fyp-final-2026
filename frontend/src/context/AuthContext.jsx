import { createContext, useContext, useEffect, useState } from "react";
import { api, onSessionEnded } from "../api";

// The JWT is kept in memory + localStorage (a demo-appropriate choice —
// see the report's discussion of XSS-vs-CSRF trade-offs for storing tokens
// in localStorage vs an httpOnly cookie). It is never logged.
const AuthContext = createContext(null);

const TOKEN_STORAGE_KEY = "mindsync_token";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadUser() {
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }
      // A wrong or expired login (401/403) signs the student out. A busy or briefly unreachable server must NOT: try again, and keep the login.
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          const me = await api.me(token);
          if (!cancelled) setUser(me);
          break;
        } catch (err) {
          if (err?.status === 401 || err?.status === 403) {
            if (!cancelled) {
              setToken(null);
              localStorage.removeItem(TOKEN_STORAGE_KEY);
            }
            break;
          }
          if (attempt < 2) await new Promise((r) => setTimeout(r, 800 * (attempt + 1)));
        }
      }
      if (!cancelled) setLoading(false);
    }

    loadUser();
    return () => {
      cancelled = true;
    };
  }, [token]);

  // A request found the login expired (it lasts 60 minutes): sign out and show the login page with a friendly note.
  useEffect(() => {
    onSessionEnded((message) => {
      try { sessionStorage.setItem("mindsync_reset_flash", message); } catch { /* the note is optional */ }
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      setToken(null);
      setUser(null);
    });
    return () => onSessionEnded(null);
  }, []);

  function login(newToken) {
    localStorage.setItem(TOKEN_STORAGE_KEY, newToken);
    setToken(newToken);
  }

  function logout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
  }

  async function refreshUser() {
    if (!token) return;
    try {
      setUser(await api.me(token));
    } catch {
      /* keep the old details; the next page load will sort out an expired login */
    }
  }

  return (
    <AuthContext.Provider value={{ token, user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
