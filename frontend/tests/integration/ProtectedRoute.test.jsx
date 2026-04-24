import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ProtectedRoute from "../../src/components/ProtectedRoute.jsx";
import { AuthProvider } from "../../src/context/AuthContext.jsx";
import { resetMockState, seedUser } from "../mocks/authHandlers.js";

function renderApp(initialEntries = ["/dashboard"]) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/login" element={<h1>Login page</h1>} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <h1>Secret dashboard</h1>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    resetMockState();
  });

  it("redirects to /login when the user is anonymous", async () => {
    renderApp();
    expect(await screen.findByText("Login page")).toBeInTheDocument();
    expect(screen.queryByText("Secret dashboard")).not.toBeInTheDocument();
  });

  it("renders children when the user is authenticated", async () => {
    seedUser({ email: "dash@example.com", password: "pw", nickname: "Dash", authenticated: true });
    renderApp();
    expect(await screen.findByText("Secret dashboard")).toBeInTheDocument();
  });
});
