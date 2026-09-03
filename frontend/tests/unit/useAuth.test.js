import React from "react";
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { AuthProvider } from "../../src/context/AuthContext.jsx";
import { useAuth } from "../../src/hooks/useAuth.js";
import { resetMockState, seedUser, setCurrentUser } from "../mocks/authHandlers.js";

function wrapper({ children }) {
  return React.createElement(AuthProvider, null, children);
}

describe("useAuth", () => {
  beforeEach(() => {
    resetMockState();
  });

  it("loads an authenticated session on mount when /auth/me returns 200", async () => {
    seedUser({ email: "me@example.com", password: "pw", nickname: "Me", authenticated: true });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.status).toBe("authenticated");
    });
    expect(result.current.user?.email).toBe("me@example.com");
  });

  it("marks the session as anonymous when /auth/me returns 401", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.status).toBe("anonymous");
    });
    expect(result.current.user).toBeNull();
  });

  it("updates status to authenticated after logging in via hook", async () => {
    seedUser({ email: "login@example.com", password: "hunter2-abc", nickname: "Login" });
    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.status).toBe("anonymous"));

    await act(async () => {
      await result.current.login({ email: "login@example.com", password: "hunter2-abc" });
    });

    expect(result.current.status).toBe("authenticated");
    expect(result.current.user?.email).toBe("login@example.com");
  });

  it("logout clears user and status", async () => {
    seedUser({ email: "out@example.com", password: "pw", nickname: "Out", authenticated: true });
    setCurrentUser("out@example.com");
    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.status).toBe("authenticated"));

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.status).toBe("anonymous");
    expect(result.current.user).toBeNull();
  });
});
