import { createContext, useCallback, useEffect, useState } from "react";
import { request, ApiError } from "../api/authApi.js";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await request("/auth/me");
        if (cancelled) return;
        setUser(me);
        setStatus("authenticated");
      } catch {
        if (cancelled) return;
        setUser(null);
        setStatus("anonymous");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const register = useCallback(async ({ email, password, nickname }) => {
    const payload = { email, password };
    if (nickname) {
      payload.nickname = nickname;
    }
    const data = await request("/auth/register", { method: "POST", body: payload });
    setUser(data);
    setStatus("authenticated");
    return data;
  }, []);

  const login = useCallback(async ({ email, password }) => {
    const data = await request("/auth/login", { method: "POST", body: { email, password } });
    setUser(data);
    setStatus("authenticated");
    return data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await request("/auth/logout", { method: "POST" });
    } catch {
      // ignore server errors on logout; always clear client state
    }
    setUser(null);
    setStatus("anonymous");
  }, []);

  const value = { user, status, register, login, logout, setStatus, setUser };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export { ApiError };
