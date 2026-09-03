import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import DeleteAccountModal from "../../src/components/DeleteAccountModal.jsx";
import { AuthContext } from "../../src/context/AuthContext.jsx";
import { resetProfileMockState, seedProfile } from "../mocks/profileHandlers.js";

function renderWithRouter(ui, { route = "/profile" } = {}) {
  return render(
    <AuthContext.Provider value={{ setUser: vi.fn(), setStatus: vi.fn() }}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/profile" element={ui} />
          <Route path="/login" element={<h1>Login page</h1>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe("DeleteAccountModal", () => {
  beforeEach(() => {
    resetProfileMockState();
    seedProfile({
      id: "00000000-0000-0000-0000-000000000001",
      nickname: "alice",
      email: "alice@example.com",
      avatar_url: null,
      linked_games: [],
      lol_stats: null,
    });
  });

  it("disables button until confirmation matches nickname", async () => {
    const user = userEvent.setup();
    renderWithRouter(<DeleteAccountModal nickname="alice" onClose={vi.fn()} />);

    const button = screen.getByRole("button", { name: "Confirmar eliminación" });
    expect(button).toBeDisabled();

    const input = screen.getByLabelText("Confirmación");
    await user.type(input, "Alice");
    expect(button).toBeDisabled();

    await user.clear(input);
    await user.type(input, "alice");
    expect(button).toBeEnabled();
  });

  it("submits delete and redirects on 204", async () => {
    const user = userEvent.setup();
    renderWithRouter(<DeleteAccountModal nickname="alice" onClose={vi.fn()} />);

    const input = screen.getByLabelText("Confirmación");
    await user.type(input, "alice");
    await user.click(screen.getByRole("button", { name: "Confirmar eliminación" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Login page" })).toBeInTheDocument();
  });

  it("shows tournament-active message on 409", async () => {
    seedProfile({
      id: "00000000-0000-0000-0000-000000000001",
      nickname: "alice",
      email: "alice@example.com",
      avatar_url: null,
      linked_games: [],
      lol_stats: null,
      has_active_tournament: true,
    });

    const user = userEvent.setup();
    renderWithRouter(<DeleteAccountModal nickname="alice" onClose={vi.fn()} />);

    const input = screen.getByLabelText("Confirmación");
    await user.type(input, "alice");
    await user.click(screen.getByRole("button", { name: "Confirmar eliminación" }));

    expect(
      await screen.findByText(/Tienes torneos activos en curso/i),
    ).toBeInTheDocument();
  });
});
