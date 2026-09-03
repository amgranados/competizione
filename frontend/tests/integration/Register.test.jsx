import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import Register from "../../src/pages/Register.jsx";
import { AuthProvider } from "../../src/context/AuthContext.jsx";
import { resetMockState } from "../mocks/authHandlers.js";

function renderWithRouter(initialEntries = ["/register"]) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<h1>Home</h1>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("Register page", () => {
  beforeEach(() => {
    resetMockState();
  });

  it("registers a new user and redirects to home on success", async () => {
    const user = userEvent.setup();
    renderWithRouter();

    await user.type(screen.getByLabelText(/email/i), "new@example.com");
    await user.type(screen.getByLabelText(/contraseña/i), "hunter2-abc");
    await user.type(screen.getByLabelText(/nickname/i), "Newbie");
    await user.click(screen.getByRole("button", { name: /crear cuenta/i }));

    expect(await screen.findByText("Home")).toBeInTheDocument();
  });

  it("shows a specific error message when the email is already taken", async () => {
    const user = userEvent.setup();
    renderWithRouter();

    await user.type(screen.getByLabelText(/email/i), "dup@example.com");
    await user.type(screen.getByLabelText(/contraseña/i), "hunter2-abc");
    await user.click(screen.getByRole("button", { name: /crear cuenta/i }));
    await screen.findByText("Home");

    renderWithRouter();
    await user.type(screen.getByLabelText(/email/i), "dup@example.com");
    await user.type(screen.getByLabelText(/contraseña/i), "hunter2-abc");
    await user.click(screen.getByRole("button", { name: /crear cuenta/i }));

    expect(await screen.findByText(/email ya está en uso/i)).toBeInTheDocument();
  });
});
