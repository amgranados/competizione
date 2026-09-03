import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import Login from "../../src/pages/Login.jsx";
import { AuthProvider } from "../../src/context/AuthContext.jsx";
import { resetMockState, seedUser } from "../mocks/authHandlers.js";

function renderFlow() {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<h1>Home</h1>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("Login page", () => {
  beforeEach(() => {
    resetMockState();
  });

  it("logs in with correct credentials and redirects home", async () => {
    seedUser({ email: "good@example.com", password: "hunter2-abc", nickname: "Good" });
    const user = userEvent.setup();
    renderFlow();

    await user.type(screen.getByLabelText(/email/i), "good@example.com");
    await user.type(screen.getByLabelText(/contraseña/i), "hunter2-abc");
    await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    expect(await screen.findByText("Home")).toBeInTheDocument();
  });

  it("shows the generic error message on wrong credentials", async () => {
    const user = userEvent.setup();
    renderFlow();

    await user.type(screen.getByLabelText(/email/i), "unknown@example.com");
    await user.type(screen.getByLabelText(/contraseña/i), "whatever-long");
    await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    expect(await screen.findByText("Credenciales inválidas")).toBeInTheDocument();
  });
});
